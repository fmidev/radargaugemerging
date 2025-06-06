import numpy as np
import argparse
import datetime
from pathlib import Path
import json
import configparser
import os

import util
import exporters
import collect_radar_gauge_pairs
import fit_kriging_model
import compute_kriged_correction_factors


def main():

    # Read run config
    run_conf_file = f"/config/{args.config}/run_config.json"
    with open(run_conf_file, "r") as jsonfile:
        run_conf = json.load(jsonfile)
    
    # Calculate previous timestamp (3 - 6 hours before the given timestamp)
    timestamp = args.timestamp
    timestamp_formatted = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M")
    rg_pairs_timeperiod = run_conf["run_options"]["rg_pairs_timeperiod"]
    rg_pairs_timeperiod_mins = rg_pairs_timeperiod*60
    earlier_timestamp = ( timestamp_formatted - datetime.timedelta(minutes=rg_pairs_timeperiod_mins) ).strftime("%Y%m%d%H%M")
            
    # Collect the gauge-radar pair file
    radargauge_file = f'{args.outpath}/{run_conf["run_options"]["rg_pairs_filename"].format(config=args.config,timestamp=timestamp)}'
    n_radargaugepairs, nodata_mask = collect_radar_gauge_pairs.run(earlier_timestamp, timestamp, radargauge_file, args.config)

    # Correction factor filename
    correction_factor_file_without_extension = f'{args.outpath}/{run_conf["run_options"]["gaugecorrfile_without_ext"].format(config=args.config,timestamp=timestamp)}'
    
    if n_radargaugepairs > 5:    
        # Fit kriging model
        kriging_model_file = f"{args.outpath}/kriging_model_{args.config}_{timestamp}.pkl"
        fit_kriging_model.run(radargauge_file, kriging_model_file, args.config)

        # Read snowprob observations to take into account when writing the output geotiff
        snowprob_conf = run_conf["snowprob"]
        snowprob_array = util.read_snowprob(timestamp_formatted, snowprob_conf)
        print("snowprob_array: ", snowprob_array)
    
        # Compute kriged correction factor
        compute_kriged_correction_factors.run(kriging_model_file, timestamp, correction_factor_file_without_extension, args.config, nodata_mask, snowprob_array)

    else:
        print(f"Too few ({n_radargaugepairs}) radar-gauge pairs found, not calculating correction factor for timestamp {timestamp}. Writing zero array instead.")

        # read configuration file for writing the Geotiff
        config = configparser.ConfigParser()
        config.read(
            os.path.join("config", args.config, "compute_kriged_correction_factors.cfg")
        )

        n_pixels_x = int(config["grid"]["n_pixels_x"])
        n_pixels_y = int(config["grid"]["n_pixels_y"])

        zeros_array = np.zeros((n_pixels_y, n_pixels_x))
        
        if config["output"]["type"] == "geotiff":
            pr = pyproj.Proj(config["grid"]["projection"])
            ll_x, ll_y = pr(config["grid"]["ll_lon"], config["grid"]["ll_lat"])
            ur_x, ur_y = pr(config["grid"]["ur_lon"], config["grid"]["ur_lat"])                                                            
            bounds = [ll_x, ll_y, ur_x, ur_y]
            fn = correction_factor_file_without_extension + ".tif"
            exporters.export_geotiff(fn, zeros_array, config["grid"]["projection"], bounds)           

        elif config["output"]["type"] == "numpy":
            np.savez_compressed(correction_factor_file_without_extension, corr=zeros_array, corr_var=zeros_array)

        else:
            raise ValueError(
                f"Output format {config['output']['type']} not supported. The valid options are 'geotiff' and 'numpy'"
            )

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
