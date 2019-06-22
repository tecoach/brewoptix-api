REGION=$1
STAGE=$2

echo "Deploy q_purchase_orders service"
cd $PWD/services/q_purchase_orders || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

echo "Iterate through all Purchase Orders and send SNS notifications"
cd $PWD/deployment_scripts/12_BREWAPI_111 || exit
python process_all_po.py $REGION $STAGE
cd ../..