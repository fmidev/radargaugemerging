# For a give date range, this script fetches radar and gauge data from the 
# FMI databases and fits a regression model for the gauge-radar adjustments.

import argparse
import configparser
from datetime import datetime, timedelta
import os
from cldb import cldb, conversions
import radar_archive

argparser = argparse.ArgumentParser()
argparser.add_argument("startdate", type=str, help="start date (YYYYMMDDHHMM)")
argparser.add_argument("enddate",   type=str, help="end date (YYYYMMDDHHMM)")
argparser.add_argument("profile",   type=str, help="configuration profile to use")
args = argparser.parse_args()

startdate = datetime.strptime(args.startdate, "%Y%m%d%H%M")
enddate   = datetime.strptime(args.enddate,   "%Y%m%d%H%M")

config = configparser.ConfigParser(interpolation=None)
config.read(os.path.join("config", args.profile, "datasources.cfg"))

config_radar = config["radar"]
config_gauge = config["gauge"]

browser = radar_archive.Browser(config_radar["root_path"],  config_radar["path_fmt"], 
                                config_radar["fn_pattern"], config_radar["fn_ext"], 
                                int(config_radar["timestep"]))

curdate = startdate
R = {}
while curdate <= enddate:
  fn = browser.listfiles(curdate)
  # TODO: Implement your own importer for reading the radar data. This is for 
  # testing purposes.
  from numpy import random
  R[fn[1][0]] = random.normal(size=(1000, 1000))
  #
  curdate += timedelta(minutes=int(config_radar["timestep"]))

cldb_client = cldb.CLDBClient(config_gauge["cldb_username"], 
                              config_gauge["cldb_password"])

cols = ["lpnn", "lat", "lat_sec", "lon", "lon_sec", "grlat", "grlon", 
        "nvl(elstat,0)"]
col_names = ["lpnn", "lat", "lat_sec", "lon", "lon_sec", "grlat", "grlon", 
             "elstat"]

gauges = cldb_client.query_stations_fmi(cols, column_names=col_names)
gauges = conversions.station_list_to_lonlatalt(gauges)

if config_gauge["gauge_type"] == "intensity":
  gauge_obs = cldb_client.query_precip_int(args.startdate, args.enddate, 50, 
    sort_by_timestamp=True, convert_timestamps=True)
else:
  gauge_obs = cldb_client.query_precip_accum_fmi(args.startdate, args.enddate, 
    int(config_gauge["accum_time"]), 50, sort_by_timestamp=True, 
    convert_timestamps=True)

# TODO ...

