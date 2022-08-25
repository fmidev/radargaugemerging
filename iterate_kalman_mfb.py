"""Iteratively apply Kalman filter to produce mean field bias (MFB) estimates.
The method is described in:

S. Chumchean, A. Seed and A. Sharma, Correcting of real-time radar rainfall
bias using a Kalman filtering approach, Journal of Hydrology 317, 123-137,
2006.

Input
-----
- Radar-gauge pair file produced by running collect_radar_gauge_pairs.py.
- Previous MFB estimator state produced by running this script. If not given,
  a new estimator is initialized.

Output
------
- The current MFB estimator state obtained by updating the Kalman filter. The
update is done by using the previous Kalman filter prediction and the MFB
computed from the current observations.

Configuration files (in the config/<profile> directory)
-------------------------------------------------------
- kalman_filter_mfb.cfg
"""

import argparse
import configparser
from datetime import datetime
import os
import pickle

import numpy as np

from kalman_mfb import KalmanFilterMFB

argparser = argparse.ArgumentParser()
argparser.add_argument("date", type=str, help="date (YYYYmmddHHMM)")
argparser.add_argument("infile", type=str, help="radar-gauge pair file")
argparser.add_argument("outfile", type=str, help="output file")
argparser.add_argument("profile", type=str, help="configuration profile to use")
argparser.add_argument(
    "--prevstatefile",
    type=str,
    help="file containing the previous Kalman MFB state",
    default=None,
)
args = argparser.parse_args()

config = configparser.ConfigParser()
config.optionxform = lambda x: x
config.read(os.path.join("config", args.profile, "kalman_filter_mfb.cfg"))

kalman_params = dict([(k, float(v)) for (k, v) in config["kalman_params"].items()])

date = datetime.strptime(args.date, "%Y%m%d%H%M")

radar_gauge_pairs = pickle.load(open(args.infile, "rb"))

if args.prevstatefile is None:
    kalman_mfb = KalmanFilterMFB(**kalman_params)
    print("No previous state file given, initialized Kalman filter from scratch.")
else:
    print(f"Read Kalman filter state from {args.prevstatefile}.")
    with open(args.prevstatefile, "rb") as f:
        prev_state = pickle.load(f)
        kalman_mfb = prev_state["kalman_mfb"]
        pred_state = prev_state["pred_state"]

    Y = 0.0
    n = 0
    for ts in radar_gauge_pairs.keys():
        if ts == date:
            for p in radar_gauge_pairs[ts]:
                Y += np.log10(p[1] / p[0])
                n += 1

    if n > 0:
        Y /= n
    else:
        Y = None

    print(f"Computed log-mean field bias = {Y:.3f} from observations at {str(date)}.")

    kalman_mfb.update(pred_state[0], pred_state[1], Y)

    print(f"Kalman state after update = ({kalman_mfb.beta:.3f}, {kalman_mfb.P:.3f}).")

corr_factor = 10 ** (kalman_mfb.beta + 0.5 * kalman_mfb.P)

print(f"Estimated correction factor = {corr_factor:.03f}")

beta_minus_pr, p_minus_pr = kalman_mfb.predict()

print(
    f"Next predicted Kalman state: beta_minus = {beta_minus_pr:.3f}, p_minus = {p_minus_pr:.3f}"
)

with open(args.outfile, "wb") as f:
    print(f"Wrote updated Kalman filter and next predicted state to {args.outfile}.")
    out_dict = {
        "kalman_mfb": kalman_mfb,
        "pred_state": (beta_minus_pr, p_minus_pr),
        "corr_factor": corr_factor,
    }
    pickle.dump(out_dict, f)
