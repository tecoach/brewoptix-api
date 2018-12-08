REGION=$1
STAGE=$2

echo "Creating projection_locks table"
cd $PWD/deployment_scripts/11_BREWAPI_112 || exit
python create_projection_locks_table.py $REGION $STAGE
cd ../..

echo "Deploy on-hand service"
cd $PWD/services/on_hand || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit
