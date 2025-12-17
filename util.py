"""Miscellaneous utility functions."""

from collections import defaultdict
from datetime import datetime, timedelta
import requests

import numpy as np
from pathlib import Path
import hiisi
from scipy.spatial import KDTree


def compute_gauge_accumulations(gauge_obs, accum_period, timestep):
    """Compute accumulated rainfall from gauge observations read by using
    query_rain_gauges. Time periods with one or more missing observations are
    skipped.
    Parameters
    ----------
    gauge_obs : list
        List of gauge observation tuples. See the output of query_rain_gauges.
    accum_period : int
        Length of the accumulation period (minutes).
    timestep : int
        Time step between gauge observations (minutes).
    Returns
    -------
    out : list
        List of triplets having the same elements as the output of
        query_rain_gauges.
    """
    gauge_obs_dict = defaultdict(dict)
    for g in gauge_obs:
        gauge_obs_dict[g[1]][g[0]] = g[2]
    out = []
    for sid in gauge_obs_dict.keys():
        startdate = min(gauge_obs_dict[sid].keys())
        enddate = max(gauge_obs_dict[sid].keys())
        curdate = startdate
        while curdate <= enddate:
            curdate_window = curdate - timedelta(minutes=accum_period)
            missing_data = False
            accum = 0
            while curdate_window <= curdate:
                if curdate_window in gauge_obs_dict[sid].keys():
                    v = gauge_obs_dict[sid][curdate_window]
                    if np.isfinite(v):
                        accum += v
                    else:
                        missing_data = True
                else:
                    missing_data = True
                curdate_window = curdate_window + timedelta(minutes=timestep)
            if not missing_data:
                out.append((curdate, sid, accum))
            curdate = curdate + timedelta(minutes=timestep)
    return out


def compute_mask_boundary_weights(mask, max_dist):
    """Compute smooth weights around a boolean image mask by applying
    the logistic function.

    Parameters
    ----------
    mask : array_like
        Boolean mask with True/False corresponding to valid/invalid pixels.
    max_dist : float
        Maximum distance from the nearest valid pixel for nonzero weights.

    Returns
    -------
    out : numpy.ndarray
        Weights around nonzero values in mask with decreasing value as a
        function of distance. Values are in the range [0, 1].
    """
    weights = np.zeros(mask.shape)

    coords = np.where(mask)

    tree = KDTree(np.column_stack([coords[0], coords[1]]))
    coords_compl = np.where(~mask)
    d, _ = tree.query(
        np.column_stack([coords_compl[0], coords_compl[1]]),
        k=1,
        distance_upper_bound=max_dist,
    )

    weights[mask] = 1

    def f(x):
        out = np.zeros(x.shape)
        mask = x <= max_dist
        out[mask] = 1 / (1 + np.exp(-x[mask]))

        return out

    weights[coords_compl[0], coords_compl[1]] = f(-(d - 0.5 * max_dist) / max_dist * 10)

    return weights


def compute_distance_to_nearest_radar(gauge_loc, radar_locs):
    """Compute the distance of the given gauge location to the nearest radar.

    Parameters
    ----------
    gauge_loc : array_like
        x- and y-coordinates of the gauge
    radar_locs : dict
        Dictionary with tuples containing x- and y-coordinates of radars.

    Returns
    -------
    out : float
        Distance to the nearest radar.
    """
    dists = [
        np.linalg.norm(np.array(gauge_loc) - np.array(radar_locs[k])) / 1000
        for k in radar_locs.keys()
    ]
    return np.min(dists)


def compute_gridded_distances_to_nearest_points(
    grid_ll_x, grid_ll_y, grid_ur_x, grid_ur_y, n_pixels_x, n_pixels_y, radar_locs
):
    """Compute distance of the given location to the nearest radar in a grid.

    Parameters
    ----------
    grid_ll_x : float
        X-coordinate of the lower-left corner of the grid.
    grid_ll_y : float
        Y-coordinate of the lower-left corner of the grid.
    grid_ur_x : float
        X-coordinate of the upper-right corner of the grid.
    grid_ur_y : float
        Y-coordinate of the upper-right corner of the grid.
    n_pixels_x : int
        Number of grid pixels in x-direction.
    n_pixels_y : int
        Number of grid pixels in y-direction.

    Returns
    -------
    out : numpy.ndarray
        Gridded distances to the nearest radar.
    """
    x = np.linspace(grid_ll_x, grid_ur_x, n_pixels_x + 1)[:-1]
    x += 0.5 * (x[1] - x[0])
    y = np.linspace(grid_ll_y, grid_ur_y, n_pixels_y + 1)[:-1]
    y += 0.5 * (y[1] - y[0])
    grid_x, grid_y = np.meshgrid(x, y)

    dist_grid = np.ones(grid_x.shape) * np.inf
    for k in radar_locs.keys():
        dx = np.array(radar_locs[k][0]) - grid_x
        dy = np.array(radar_locs[k][1]) - grid_y
        dist_grid_cur = np.sqrt(dx * dx + dy * dy) / 1000.0
        dist_grid = np.minimum(dist_grid, dist_grid_cur)

    return dist_grid


def query_rain_gauges(
    startdate, enddate, config, ll_lon=None, ll_lat=None, ur_lon=None, ur_lat=None
):
    """Query rain gauge observations and the corresponding gauge locations from
    SmartMet in the given date range.

    Parameters
    ----------
    startdate : datetime.datetime
        Start date for querying the gauge observations.
    enddate : datetime.datetime
        End date for querying the gauge observations.
    config : dict
        Configuration dictionary read from datasources.cfg, gauge subsection.
    ll_lon, ll_lat, ur_lon, ur_lat : float
        Bounding box coordinates. Gauges outside the box are not included.

    Returns
    -------
    out : tuple
        Two-element tuple containing gauge locations and gauge observations.
    """
    payload = {
        "bbox": "18.6,57.93,34.903,69.005",
        "producer": "observations_fmi",
        "param": "stationname,"
        "fmisid,"
        "utctime,"
        "latitude,"
        "longitude," + config["gauge_type"],
        "starttime": datetime.strftime(startdate - timedelta(hours=3), "%Y%m%dT%H%M"),
        "endtime": datetime.strftime(enddate + timedelta(hours=3), "%Y%m%dT%H%M"),
        "timestep": "data",
        "format": "json",
    }

    result = requests.get("http://smartmet.fmi.fi/timeseries", params=payload).json()

    gauge_lonlat = set()
    gauge_obs = []
    for i, r in enumerate(result):
        obstime = datetime.strptime(r["utctime"], "%Y%m%dT%H%M%S")
        if obstime < startdate or obstime > enddate:
            continue
        fmisids = r["fmisid"].strip("[").strip("]").split(" ")
        longitudes = [float(v) for v in r["longitude"].strip("[").strip("]").split(" ")]
        latitudes = [float(v) for v in r["latitude"].strip("[").strip("]").split(" ")]
        observations = [
            float(v) for v in r[config["gauge_type"]].strip("[").strip("]").split(" ")
        ]
        for fmisid, lon, lat, obs in zip(fmisids, longitudes, latitudes, observations):
            if fmisid != "nan":
                if ll_lon is not None and lon < ll_lon:
                    continue
                if ll_lat is not None and lat < ll_lat:
                    continue
                if ur_lon is not None and lon > ur_lon:
                    continue
                if ur_lat is not None and lat > ur_lat:
                    continue
                gauge_lonlat.add((fmisid, lon, lat))
                gauge_obs.append((obstime, fmisid, obs))

    return gauge_lonlat, gauge_obs


def read_radar_locations(config):
    """Read radar locations from configuration file.

    Parameters
    ----------
    config : dict
        Dictionary read from radar_locations.yaml.

    Returns
    -------
    out : dict
        Dictionary containing radar longitudes and latitudes.
    """
    out = {}
    for radar in config.keys():
        out[radar] = tuple([float(v) for v in config[radar].split(",")])

    return out


def read_snowprob(curdate, snowprob_conf):
    """Read probability of snow data.              
    Allows searching some timesteps bawckwards, if file does not exist for                   
    the current timestep. The allowed time difference should be defined
    as minutes with the key "allow_timediff" in the snowprob_conf;
    otherwise 5 minutes is used.
 
    Parameters                                                        
    ----------                                          
    curdate : datetime                                          
        The current time.                                  
    snowprob_conf : dict                               
        The configuration for the snow probability data. Should include keys
        "dir", "filename", "timeres", "allow_timediff".
                                             
    Returns 
    -------                                                        
    np.ndarray                                             
        The snow probability data.

    """
    
    path = Path(snowprob_conf["dir"])                           
    curfile = path / snowprob_conf["filename"].format(timestamp=curdate.strftime("%Y%m%d%H%M"))
    allowed_timediff = snowprob_conf.get("allow_timediff", 5) * 60
    
    prev_time = curdate
    while not curfile.exists():
        # Find the previous file
        timediff = curdate - prev_time
        if timediff.total_seconds() > allowed_timediff:
            raise FileNotFoundError(
                f"Could not find snow probability file for {curdate} or older, tried up to {prev_time}"
            )
        prev_time = prev_time - timedelta(minutes=snowprob_conf["timeres"])
        curfile = path / snowprob_conf["filename"].format(timestamp=prev_time.strftime("%Y%m%d%H%M"))
        
    (
        snowprob,
        snowprob_quantity,
        snowprob_timestamp,
        snowprob_gain,
        snowprob_offset,
        snowprob_nodata,
        snowprob_undetect,
    ) = read_hdf5(curfile, qty="SNOWPROB")
    
    snowprob = snowprob.astype(np.float32)
    snowprob[snowprob == snowprob_nodata] = np.nan
    snowprob[snowprob == snowprob_undetect] = 0
    
    return snowprob


def read_hdf5(image_h5_file, qty="DBZH"):
    """Read image array from ODIM hdf5 file.

    Keyword arguments:
    image_h5_file -- ODIM hdf5 file
    qty -- array quantity that is read                                                                                                                  

    Return:
    image_array -- numpy array containing DBZH or RATE array
    quantity -- array quantity
    timestamp -- timestamp of image_array
    mask_nodata -- masked array where image_array has nodata value
    gain -- gain of image_array
    offset -- offset of image_array
    """
    
    # Read RATE or DBZH from hdf5 file
    comp = hiisi.OdimCOMP(image_h5_file, "r")
    test = comp.select_dataset(qty)

    if test is not None:
        image_array = comp.dataset
        quantity = qty
    else:
        raise ValueError(f"{qty} array not found in the file {image_h5_file}!")

    # Read nodata and undetect values from metadata for masking
    gen = comp.attr_gen("nodata")
    pair = gen.__next__()
    nodata = pair.value
    gen = comp.attr_gen("undetect")
    pair = gen.__next__()
    undetect = pair.value

    # Read gain and offset values from metadata
    gen = comp.attr_gen("gain")
    pair = gen.__next__()
    gain = pair.value
    gen = comp.attr_gen("offset")
    pair = gen.__next__()
    offset = pair.value

    # Read timestamp from metadata
    gen = comp.attr_gen("date")
    pair = gen.__next__()
    date = pair.value
    gen = comp.attr_gen("time")
    pair = gen.__next__()
    time = pair.value
    timestamp = date + time

    return image_array, quantity, timestamp, gain, offset, int(nodata), int(undetect)
