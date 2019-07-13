#!/usr/bin/env bash
# Sourcing dynamo local config variables
# Please make sure the initialize and stop script are run from parent directory
. dynamodb_local_scripts/dynamodb_local_config.sh

if [ "$(docker ps -q -f name=$DYNAMO_LOCAL_CONTAINER_NAME)" ]; then
    docker stop $DYNAMO_LOCAL_CONTAINER_NAME
fi