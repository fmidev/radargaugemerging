# For a give date range, this script fetches radar and gauge data from the
# FMI databases and fits a regression model for the gauge-radar adjustments.

import argparse
from collections import defaultdict
import configparser
from datetime import datetime, timedelta
import numpy as np
import os
import pyproj
import sys
from cldb import cldb, conversions
import radar_archive

# Parse command-line arguments.
argparser = argparse.ArgumentParser()
argparser.add_argument("startdate", type=str, help="start date (YYYYMMDDHHMM)")
argparser.add_argument("enddate", type=str, help="end date (YYYYMMDDHHMM)")
argparser.add_argument("profile", type=str, help="configuration profile to use")
args = argparser.parse_args()

startdate = datetime.strptime(args.startdate, "%Y%m%d%H%M")
enddate = datetime.strptime(args.enddate, "%Y%m%d%H%M")

# Read the configuration files.
config = configparser.ConfigParser(interpolation=None)
config.read(os.path.join("config", args.profile, "datasources.cfg"))

config_radar = config["radar"]
config_gauge = config["gauge"]

browser = radar_archive.Browser(
    config_radar["root_path"],
    config_radar["path_fmt"],
    config_radar["fn_pattern"],
    config_radar["fn_ext"],
    int(config_radar["timestep"]),
)

# Read radar data from the archive.
# TODO: Check the availability of gauge data first, and based on that, read
# only the radar data that is needed.
curdate = startdate
R = {}
while curdate <= enddate:
    fn = browser.listfiles(curdate)

    print("Reading input file %s... " % os.path.basename(fn[0][0]), end="")

    sys.stdout.flush()
    # TODO: Implement your own importer for reading the radar data. This is for
    # testing purposes.
    from numpy import random

    R[fn[1][0]] = random.normal(size=(1000, 1000))
    #

    print("Done.")

    curdate += timedelta(minutes=int(config_radar["timestep"]))

# Read gauge data from the cldb database.
cldb_client = cldb.CLDBClient(
    config_gauge["cldb_username"], config_gauge["cldb_password"]
)

cols = ["lpnn", "lat", "lat_sec", "lon", "lon_sec", "grlat", "grlon", "nvl(elstat,0)"]
col_names = ["lpnn", "lat", "lat_sec", "lon", "lon_sec", "grlat", "grlon", "elstat"]

print("Querying gauge locations from the database... ", end="")
sys.stdout.flush()

gauges = cldb_client.query_stations_fmi(cols, column_names=col_names)
gauges = conversions.station_list_to_lonlatalt(gauges)

# convert the lon-lat coordinates into grid coordinates (pixels)
pr = pyproj.Proj(config_radar["projection"])

x1, y1 = pr(config_radar["bbox_ll_lon"], config_radar["bbox_ll_lat"])
x2, y2 = pr(config_radar["bbox_ur_lon"], config_radar["bbox_ur_lat"])

R_shape = list(R.values())[0].shape

for g in gauges:
    lon, lat = g[1], g[2]
    x, y = pr(lon, lat)
    x = (x - x1) / (x2 - x1) * (R_shape[1] - 1) + 0.5
    y = (y2 - y) / (y2 - y1) * (R_shape[0] - 1) + 0.5
    g[1] = x
    g[2] = y

print("Done.")

print("Reading gauge measurements from the database... ", end="")
sys.stdout.flush()

if config_gauge["gauge_type"] == "intensity":
    gauge_obs = cldb_client.query_precip_int(
        args.startdate,
        args.enddate,
        50,
        sort_by_timestamp=True,
        convert_timestamps=True,
    )
else:
    gauge_obs = cldb_client.query_precip_accum_fmi(
        args.startdate,
        args.enddate,
        int(config_gauge["accum_time"]),
        50,
        sort_by_timestamp=True,
        convert_timestamps=True,
    )

print("Done.")

# Arrange gauge locations into a dictionary.
gauges_ = {}
for r in gauges:
    r = tuple(r)
    gauges_[r[0]] = r[1:]
gauges = gauges_

# Arrange gauge observations into a dictionary.
# gauge_obs = dict([(r[0], r[1:]) for r in gauge_obs])
gauge_obs_ = defaultdict(list)
for r in gauge_obs:
    r = tuple(r)
    gauge_obs_[r[0]].append(r[1:])
gauge_obs = gauge_obs_

print("Collecting radar-gauge pairs... ", end="")
sys.stdout.flush()

r_sum = 0.0
g_sum = 0.0
n_samples = 0

# Collect radar-gauge pairs.
for radar_ts in sorted(R.keys()):
    R_cur = R[radar_ts]
    if radar_ts in gauge_obs.keys():
        g_cur = gauge_obs[radar_ts]
        for g in g_cur:
            lpnn = g[0]
            x, y = gauges[lpnn][0], gauges[lpnn][1]
            x_ = int(np.round(x))
            y_ = int(np.round(y))
            if x_ >= 0.0 and y_ >= 0.0 and x_ <= R_shape[1] and y_ < R_shape[0]:
                r_obs = R_cur[y_, x_]
                g_obs = g[1]
                # TODO: Make the threshold values configurable.
                if r_obs > 0.1 and g_obs > 0.1:
                    r_sum += r_obs
                    g_sum += g_obs
                    n_samples += 1

print("Done.")

MFB = 10 * np.log10(g_sum) / (10 * np.log10(r_sum))
print("MFB = %.3f , no. samples = %d" % (MFB, n_samples))
