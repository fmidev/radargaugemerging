"""Miscellaneous utility functions."""

from datetime import datetime, timedelta
import requests


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
