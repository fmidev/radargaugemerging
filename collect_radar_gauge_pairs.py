"""For the given time range, fetch radar- and gauge-based rainfall accumulations
from the FMI databases and collect co-located measurement pairs. Write the
pairs into the given file as a pickle dump."""

import argparse
from collections import defaultdict
import configparser
from datetime import datetime, timedelta
import os
import pickle
import numpy as np
import pyproj
import requests
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

browser = radar_archive.Browser(
    config_radar["root_path"],
    config_radar["path_fmt"],
    config_radar["fn_pattern"],
    config_radar["fn_ext"],
    int(config_radar["timestep"]),
)

# read radar data from the archive
curdate = startdate
radar_filenames = {}
while curdate <= enddate:
    fn = browser.listfiles(curdate)
    if os.path.exists(fn[0][0]):
        radar_filenames[fn[1][0]] = fn[0][0]
        print("Found input file %s." % os.path.basename(fn[0][0]))

    curdate += timedelta(minutes=int(config_radar["timestep"]))

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

print("done.")

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

print("Collecting radar-gauge pairs... ", end="", flush=True)

r_thr = float(config["thresholds"]["radar"])
g_thr = float(config["thresholds"]["gauge"])

radar_gauge_pairs = {}

# collect radar-gauge pairs
for radar_ts in sorted(radar_filenames.keys()):
    # TODO: Implement your own importer for reading the radar data. This is for
    # testing purposes.
    radar_rain_accum_cur = np.random.normal(size=(1000, 1000)) + 5.0
    #
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
                if r_obs >= r_thr and g_obs >= g_thr:
                    if not radar_ts in radar_gauge_pairs.keys():
                        radar_gauge_pairs[radar_ts] = []
                    radar_gauge_pairs[radar_ts].append((r_obs, g_obs))

print("done.")

print(f"Writing to output file {args.outfile}... ", end="", flush=True)

pickle.dump(radar_gauge_pairs, open(args.outfile, "wb"))

print("done.")
