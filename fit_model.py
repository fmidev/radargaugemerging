# For a give date range, this script fetches radar and gauge data from the 
# FMI databases and fits a regression model for the gauge-radar adjustments.

import argparse
import configparser
from datetime import datetime, timedelta
import os
import cldb
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

browser = radar_archive.Browser(config_radar["root_path"],  config_radar["path_fmt"], 
                                config_radar["fn_pattern"], config_radar["fn_ext"], 
                                int(config_radar["timestep"]))

curdate = startdate
while curdate <= enddate:
  radar_fn = browser.listfiles(curdate)[0]
  curdate += timedelta(minutes=int(config_radar["timestep"]))

# TODO ...

