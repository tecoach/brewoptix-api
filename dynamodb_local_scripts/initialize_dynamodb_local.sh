#!/usr/bin/env bash
# Sourcing dynamo local config variables
# Please make sure the initialize and stop script are run from parent directory
. dynamodb_local_scripts/dynamodb_local_config.sh

echo "Running Dynamodb Local Docker container:" $DYNAMO_LOCAL_CONTAINER_NAME

if [ ! "$(docker ps -q -f name=$DYNAMO_LOCAL_CONTAINER_NAME)" ]; then
    if [ "$(docker ps -aq -f status=exited -f name=$DYNAMO_LOCAL_CONTAINER_NAME)" ]; then
        # cleanup
        echo "Cleanup exited container"
        docker rm $DYNAMO_LOCAL_CONTAINER_NAME
    fi

    # run your container
    echo "run container"

    docker run --detach -p 8000:8000 --name $DYNAMO_LOCAL_CONTAINER_NAME amazon/dynamodb-local

else
    echo "$DYNAMO_LOCAL_CONTAINER_NAME already running"
fi

echo "Creating/Updating tables in dynamodb local"

# Create tables
python $PWD/data_dynamodb/create_tables.py local ${DYNAMO_ENDPOINT}

# Creating SNS and SQS stack
python $PWD/dynamodb_local_scripts/create_localstack_resources.py

# Run serverless locally
sls offline start --stage local
