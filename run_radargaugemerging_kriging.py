import collect_radar_gauge_pairs
import fit_kriging_model
import compute_kriged_correction_factors
import argparse
import datetime
from pathlib import Path


def main():
    
    # Calculate previous timestamp (3 - 6 hours before the given timestamp)
    timestamp = args.timestamp
    timestamp_formatted = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M")
    rg_pairs_timeperiod_mins = 3*60
    earlier_timestamp = ( timestamp_formatted - datetime.timedelta(minutes=rg_pairs_timeperiod_mins) ).strftime("%Y%m%d%H%M")
            
    # Collect the gauge-radar pair file
    radargauge_file = f"{args.outpath}/radargaugepairs_{args.config}_{timestamp}.dat"
    collect_radar_gauge_pairs.run(earlier_timestamp, timestamp, radargauge_file, args.config)

    # Fit kriging model
    kriging_model_file = f"{args.outpath}/kriging_model_{args.config}_{timestamp}.pkl"
    fit_kriging_model.run(radargauge_file, kriging_outfile, args.config)

    # Compute kriged correction factor
    correction_factor_file = f"{args.outpath}/radargauge_corrfactor_{args.config}_{timestamp}.tif"
    compute_kriged_correction_factor.run(kriging_model_file, timestamp, correction_factor_file, args.config)
    

if __name__ == '__main__':

    # parse command-line arguments
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--timestamp",
                           type=str,
                           default="202304111200",
                           help="timestamp (YYYYMMDDHHMM)")
    argparser.add_argument("--config",
                           type=str,
                           default="finradfast",
                           help="configuration profile to use")
    argparser.add_argument("--outpath",
                           type=str,
                           help="Path for output")
    
    
    args = argparser.parse_args()

    main()
