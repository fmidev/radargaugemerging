import collect_radar_gauge_pairs
import iterate_kalman_mfb
import argparse
import datetime
from pathlib import Path


def main():

    # Calculate previous timestamp (1 hour before latest)
    timestamp = args.timestamp
    timestamp_formatted = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M")
    previous_timestamp = ( timestamp_formatted - datetime.timedelta(minutes=60) ).strftime("%Y%m%d%H%M%S")
    
    ### Run Kalman filter-based MFB

    # Initialize MFB estimator if mfb state file does not exist
    mfb_state_file = args.mfb_state_file.format(config = args.config)
    my_file = Path(mfb_state_file)
    if not my_file.is_file():
        iterate_kalman_mfb.run(timestamp, radargauge_file, mfb_state_file, args.config, prevstatefile=None)
    
    # Collect the gauge-radar pair file
    radargauge_file = f"radargaugepairs_{timestamp}.dat"
    collect_radar_gauge_pairs.run(previous_timestamp, timestamp, radargauge_file, args.config)

    # Using the previous MFB state, we can then run
    mfb_state_file = "mfb_state.dat"
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
    argparser.add_argument("--mfb_state_file",
                           type=str,
                           default="/mfb_state_{config}.dat",
                           help="path and filename for mfb_state file")
    
    args = argparser.parse_args()

    main()
