#!/bin/bash

INPATH=${INPATH:-"/tutka/data/dev/cache/radar-composite/hulehenri_3067_500m/dbzh/andre"}
OUTPATH=${OUTPATH:-"/tutka/data/dev/cache/radar/fmippn/hulehenri/corrected_composites"}
LATEST_TIMESTAMP=`ls -t ${INPATH}/*h5 | head -1 | awk -F "/" '{print $10}' | awk -F "_" '{print $1}'`
CONFIG=${CONFIG:-"hulehenri"}
TIMESTAMP=${TIMESTAMP:-${LATEST_TIMESTAMP}}

# Make directories if they don't exist
mkdir -p $OUTPATH

# Build from Dockerfile
#docker build -t radargaugemerging .

# Run with volume mounts
docker run \
       --rm \
       --env "timestamp=$TIMESTAMP" \
       --env "config=$CONFIG" \
       --security-opt label=disable \
       --mount type=bind,source="$(pwd)"/config,target=/config \
       --mount type=bind,source=/tutka/data/storage/radargaugemerging,target=/tutka/data/storage/radargaugemerging \
       --mount type=bind,source="$(pwd)"/multiply_composite_with_calculated_factor.py,target=/multiply_composite_with_calculated_factor.py \
       --mount type=bind,source=$INPATH,target=$INPATH \
       --mount type=bind,source=$OUTPATH,target=$OUTPATH \
       radargaugemerging:latest
