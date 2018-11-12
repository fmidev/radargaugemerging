# For a give date range, this script fetches radar and gauge data from the 
# FMI databases and fits a regression model for the gauge-radar adjustments.

import argparse
import configparser
import cldb

argparser = argparse.ArgumentParser()
argparser.add_argument("startdate", type=str, help="start date (YYYYMMDDHHMM)")
argparser.add_argument("enddate",   type=str, help="end date (YYYYMMDDHHMM)")
argparser.add_argument("profile",   type=str, help="configuration profile to use")
args = argparser.parse_args()

