import collect_radar_gauge_pairs
import iterate_kalman_mfb
import argparse
import datetime
from pathlib import Path


def main():

    # Calculate previous timestamp (1 hour before latest)
    timestamp = args.timestamp
    timestamp_formatted = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M")
    timestamp_minus1h = ( timestamp_formatted - datetime.timedelta(minutes=60) ).strftime("%Y%m%d%H%M")

    # Initialize MFB estimator if mfb state file does not exist
    mfb_state_file = f"{args.path_mfb_state}/mfb_state_{args.config}.dat"
    my_file = Path(mfb_state_file)
    if not my_file.is_file():
        # Collect radar-gauge pair file for earlier timeslot and initialize mfb state file
        timestamp_minus2h = ( timestamp_formatted - datetime.timedelta(minutes=120) ).strftime("%Y%m%d%H%M")
        radargauge_file_minus1h = f"{args.path_radargaugepairs}/radargaugepairs_{args.config}_{timestamp_minus1h}.dat"
        collect_radar_gauge_pairs.run(timestamp_minus2h, timestamp_minus1h, radargauge_file_minus1h, args.config)
        iterate_kalman_mfb.run(timestamp_minus1h, radargauge_file_minus1h, mfb_state_file, args.config, prevstatefile=None)
        
    # Collect the gauge-radar pair file
    radargauge_file = f"{args.path_radargaugepairs}/radargaugepairs_{args.config}_{timestamp}.dat"
    collect_radar_gauge_pairs.run(timestamp_minus1h, timestamp, radargauge_file, args.config)

    # Run Kalman filter based MFB using the previous MFB state
    iterate_kalman_mfb.run(timestamp, radargauge_file, mfb_state_file, args.config, prevstatefile=mfb_state_file)
    

if __name__ == '__main__':

    # parse command-line arguments
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--timestamp",
                           type=str,
                           default="202304111200",
                           help="timestamp (YYYYMMDDHHMM)")
    argparser.add_argument("--config",
                           type=str,
                           default="hulehenri",
                           help="configuration profile to use")
    argparser.add_argument("--path_mfb_state",
                           type=str,
                           help="Path for mfb_state file")
    argparser.add_argument("--path_radargaugepairs",
                           type=str,
                           help="Path for radar gauge pairs files")
    
    
    args = argparser.parse_args()

    main()
