"""For the given time range, fetch radar- and gauge-based rainfall accumulations
from the FMI databases and collect co-located measurement pairs. Write the
pairs into the given file as a pickle dump."""

import argparse
from collections import defaultdict
import configparser
from datetime import datetime, timedelta
import os
import pickle
import yaml
import numpy as np
import pyproj
import requests

import importers
import radar_archive

# parse command-line arguments
argparser = argparse.ArgumentParser()
argparser.add_argument("startdate", type=str, help="start date (YYYYMMDDHHMM)")
argparser.add_argument("enddate", type=str, help="end date (YYYYMMDDHHMM)")
argparser.add_argument("outfile", type=str, help="output file")
argparser.add_argument("profile", type=str, help="configuration profile to use")
args = argparser.parse_args()

startdate = datetime.strptime(args.startdate, "%Y%m%d%H%M")
enddate = datetime.strptime(args.enddate, "%Y%m%d%H%M")

# read the configuration files
config = configparser.ConfigParser()
config.read(os.path.join("config", args.profile, "collect_radar_gauge_pairs.cfg"))

config_ds = configparser.ConfigParser(interpolation=None)
config_ds.read(os.path.join("config", args.profile, "datasources.cfg"))

config_radar = config_ds["radar"]
config_gauge = config_ds["gauge"]

with open(os.path.join("config", args.profile, "radar_locations.yaml"), "r") as f:
    config_radarlocs = yaml.safe_load(f)

radar_locs = {}
for radar in config_radarlocs.keys():
    radar_locs[radar] = tuple([float(v) for v in config_radarlocs[radar].split(",")])

radar_timestep = int(config_radar["timestep"])
radar_accum_period = int(config_ds["radar"]["accum_period"])
gauge_accum_period = int(config_ds["gauge"]["accum_period"])

browser = radar_archive.Browser(
    config_radar["root_path"],
    config_radar["path_fmt"],
    config_radar["fn_pattern"],
    config_radar["fn_ext"],
    radar_timestep,
)

# read radar file names from the archive
curdate = startdate
radar_filenames = {}

while curdate <= enddate:
    try:
        fn = browser.listfiles(curdate)

        if os.path.exists(fn[0][0]):
            radar_filenames[fn[1][0]] = fn[0][0]
            print("Found input file %s." % os.path.basename(fn[0][0]))
    except FileNotFoundError:
        pass

    curdate += timedelta(minutes=radar_accum_period)

# read gauge observations from SmartMet
cols = ["lpnn", "lat", "lat_sec", "lon", "lon_sec", "grlat", "grlon", "nvl(elstat,0)"]
col_names = ["lpnn", "lat", "lat_sec", "lon", "lon_sec", "grlat", "grlon", "elstat"]

print("Querying gauge observations from SmartMet... ", end="", flush=True)

payload = {
    "bbox": "18.6,57.93,34.903,69.005",
    "producer": "observations_fmi",
    "param": "stationname,"
    "fmisid,"
    "localtime,"
    "latitude,"
    "longitude," + config_gauge["gauge_type"],
    "starttime": datetime.strftime(startdate, "%Y-%m-%dT%H:%M:%S"),
    "endtime": datetime.strftime(enddate, "%Y-%m-%dT%H:%M:%S"),
    "timestep": "data",
    "format": "json",
}

result = requests.get("http://smartmet.fmi.fi/timeseries", params=payload).json()

gauge_lonlat = set()
gauge_obs = []
for i, r in enumerate(result):
    obstime = datetime.strptime(r["localtime"], "%Y%m%dT%H%M%S")
    fmisids = r["fmisid"].strip("[").strip("]").split(" ")
    longitudes = [float(v) for v in r["longitude"].strip("[").strip("]").split(" ")]
    latitudes = [float(v) for v in r["latitude"].strip("[").strip("]").split(" ")]
    observations = [
        float(v) for v in r[config_gauge["gauge_type"]].strip("[").strip("]").split(" ")
    ]
    for fmisid, lon, lat, obs in zip(fmisids, longitudes, latitudes, observations):
        if fmisid != "nan":
            gauge_lonlat.add((fmisid, lon, lat))
            gauge_obs.append((obstime, fmisid, obs))

# convert the lon-lat coordinates into grid coordinates (pixels)
pr = pyproj.Proj(config_radar["projection"])

x1, y1 = pr(config_radar["bbox_ll_lon"], config_radar["bbox_ll_lat"])
x2, y2 = pr(config_radar["bbox_ur_lon"], config_radar["bbox_ur_lat"])

gauge_xy = set()
for g in gauge_lonlat:
    x, y = pr(g[1], g[2])
    x = (x - x1) / (x2 - x1)
    y = (y2 - y) / (y2 - y1)
    gauge_xy.add((g[0], x, y))

print(f"{len(result)} gauges found.")

# insert gauge locations into a dictionary
gauges_ = {}
for r in gauge_xy:
    gauges_[r[0]] = r[1:]
gauges = gauges_

# insert gauge observations into a dictionary
gauge_obs_ = defaultdict(list)
for r in gauge_obs:
    gauge_obs_[r[0]].append(r[1:])
gauge_obs = gauge_obs_

print("Collecting radar-gauge pairs:")

r_thr = float(config["thresholds"]["radar"])
g_thr = float(config["thresholds"]["gauge"])

radar_gauge_pairs = {}

rgpair_attribs = config["other"]["attributes"].split(",")

gauge_lonlats = dict([(v[0], (v[1], v[2])) for v in gauge_lonlat])


def _compute_nearest_distance(gauge_lonlat):
    pass


# collect radar-gauge pairs
radar_ts = startdate
while radar_ts <= enddate:
    importer = importers.get_method(config_radar["importer"])

    # Read radar measurements from the gauge accumulation period.
    # Here we assume that the gauge values represent accumulation from the
    # previous n minutes.
    num_accum_timesteps = gauge_accum_period / radar_accum_period
    if int(num_accum_timesteps) != num_accum_timesteps:
        raise ValueError(
            "gauge accumulation period not divisible by radar accumulation period"
        )
    num_accum_timesteps = int(num_accum_timesteps)
    num_missing = 0
    num_found = 0
    radar_rain_accum_cur = 0.0

    for t in range(num_accum_timesteps):
        prev_radar_ts = radar_ts - t * timedelta(minutes=radar_accum_period)
        if not prev_radar_ts in radar_filenames.keys():
            num_missing += 1
        else:
            radar_rain_rate, _ = importer(radar_filenames[prev_radar_ts])
            radar_rain_accum_cur += radar_rain_rate
            num_found += 1

    if num_missing > int(config["missing_values"]["max_missing_radar_timestamps"]):
        print(
            f"Not enough previous files found for {radar_ts} for computing accumulated rainfall, skipping."
        )
    else:
        print(
            f"Computed radar accumulation for {radar_ts} by using observations from {num_found} timestamps."
        )
        radar_rain_accum_cur /= num_found
        radar_rain_accum_shape = radar_rain_accum_cur.shape

        if radar_ts in gauge_obs.keys():
            g_cur = gauge_obs[radar_ts]
            for g in g_cur:
                fmisid = g[0]
                x, y = gauges[fmisid][0], gauges[fmisid][1]
                x_ = int(np.floor(x * radar_rain_accum_shape[1]))
                y_ = int(np.floor(y * radar_rain_accum_shape[0]))
                if (
                    x_ >= 0.0
                    and y_ >= 0.0
                    and x_ < radar_rain_accum_shape[1]
                    and y_ < radar_rain_accum_shape[0]
                ):
                    r_obs = radar_rain_accum_cur[y_, x_]
                    g_obs = g[1]

                    if "distance" in rgpair_attribs:
                        dist = _compute_nearest_distance(gauge_lonlats[fmisid])

                    if r_obs >= r_thr and g_obs >= g_thr:
                        if not radar_ts in radar_gauge_pairs.keys():
                            radar_gauge_pairs[radar_ts] = []
                        radar_gauge_pairs[radar_ts].append((r_obs, g_obs))

    radar_ts += timedelta(minutes=gauge_accum_period)

print("done.")

print(f"Writing to output file {args.outfile}... ", end="", flush=True)

pickle.dump(radar_gauge_pairs, open(args.outfile, "wb"))

print("done.")
