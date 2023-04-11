#!/bin/bash

INPATH="/tutka/data/dev/cache/radar/fmippn/hulehenri/accrate_composites"
LATEST_TIMESTAMP=`ls -t ${INPATH}/*60min* | head -1 | awk -F "/" '{print $10}' | awk -F "_" '{print $1}'`
DOMAIN=${DOMAIN:-"hulehenri"}
TIMESTAMP=${TIMESTAMP:-${LATEST_TIMESTAMP}}

# Build from Dockerfile
#docker build -t radargaugemerging .

# Run with volume mounts
docker run \
       --rm \
       --env "timestamp=$TIMESTAMP" \
       --env "domain=$DOMAIN" \
       --security-opt label=disable \
       --mount type=bind,source="$(pwd)"/config,target=/config \
       --mount type=bind,source="$(pwd)"/run_radargaugemerging.py,target=/run_radargaugemerging.py \
       --mount type=bind,source="$(pwd)"/collect_radar_gauge_pairs.py,target=/collect_radar_gauge_pairs.py \
       --mount type=bind,source="$(pwd)"/iterate_kalman_mfb.py,target=/iterate_kalman_mfb.py \
       radargaugemerging:latest

