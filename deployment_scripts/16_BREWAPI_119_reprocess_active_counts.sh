STAGE=$1

echo "Iterate through all Latest-Active Counts and send SNS notifications"
cd $PWD/deployment_scripts/16_BREWAPI_119 || exit
python process_all_active_counts.py $STAGE
cd ../..