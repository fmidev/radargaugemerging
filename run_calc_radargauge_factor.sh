#!/bin/bash

INPATH="/tutka/data/dev/cache/radar/fmippn/hulehenri/accrate_composites"
LATEST_TIMESTAMP=`ls -t ${INPATH}/*60min* | head -1 | awk -F "/" '{print $10}' | awk -F "_" '{print $1}'`
CONFIG=${CONFIG:-"hulehenri"}
TIMESTAMP=${TIMESTAMP:-${LATEST_TIMESTAMP}}
MFB_STATE_PATH=${MFB_STATE_PATH:-"/tutka/data/storage/radargaugemerging"}
RADARGAUGEPAIRS_PATH=${RADARGAUGEPAIRS_PATH:-"/tutka/data/dev/cache/radar/radargaugemerging"}

# Make directories if they don't exist
mkdir -p $MFB_STATE_PATH
mkdir -p $RADARGAUGEPAIRS_PATH

# Build from Dockerfile
#docker build -t radargaugemerging .

# Run with volume mounts
docker run \
       --rm \
       --env "timestamp=$TIMESTAMP" \
       --env "config=$CONFIG" \
       --env "path_mfb_state=$MFB_STATE_PATH" \
       --env "path_radargaugepairs=$RADARGAUGEPAIRS_PATH" \
       --security-opt label=disable \
       --mount type=bind,source="$(pwd)"/config,target=/config \
       --mount type=bind,source="$(pwd)"/run_radargaugemerging.py,target=/run_radargaugemerging.py \
       --mount type=bind,source="$(pwd)"/collect_radar_gauge_pairs.py,target=/collect_radar_gauge_pairs.py \
       --mount type=bind,source="$(pwd)"/iterate_kalman_mfb.py,target=/iterate_kalman_mfb.py \
       --mount type=bind,source="$(pwd)"/radar_archive.py,target=/radar_archive.py \
       --mount type=bind,source="$(pwd)"/importers.py,target=/importers.py \
       --mount type=bind,source=$INPATH,target=$INPATH \
       --mount type=bind,source=$MFB_STATE_PATH,target=$MFB_STATE_PATH \
       --mount type=bind,source=$RADARGAUGEPAIRS_PATH,target=$RADARGAUGEPAIRS_PATH \
       radargaugemerging:latest

