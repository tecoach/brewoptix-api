STAGE=$1

echo "Deploy q_counts service"
cd $PWD/services/q_counts || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

echo "Iterate through all Latest-Active Counts and send SNS notifications"
cd $PWD/deployment_scripts/16_BREWAPI_119 || exit
python process_all_counts.py $STAGE
cd ../..