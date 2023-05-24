#!/bin/bash

INPATH="/tutka/data/dev/cache/radar/fmippn/hulehenri/accrate_composites"
LATEST_TIMESTAMP=`ls -t ${INPATH}/*5min* | head -1 | awk -F "/" '{print $10}' | awk -F "_" '{print $1}'`
CONFIG=${CONFIG:-"hulehenri"}
TIMESTAMP=${TIMESTAMP:-${LATEST_TIMESTAMP}}

# Build from Dockerfile
#docker build -t radargaugemerging .

# Run with volume mounts
docker run \
       --rm \
       --env "timestamp=$TIMESTAMP" \
       --env "config=$CONFIG" \
       --security-opt label=disable \
       --mount type=bind,source="$(pwd)"/config,target=/config \
       --mount type=bind,source="$(pwd)"/multiply_composite_with_calculated_factor.py,target=/multiply_composite_with_calculated_factor.py \
       --mount type=bind,source=$INPATH,target=$INPATH \
       radargaugemerging:latest
