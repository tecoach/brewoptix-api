REGION=$1
STAGE=$2

echo "Deploy new distributors service"
cd $PWD/services/distributors || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

echo "Deploy purchase-orders service"
cd $PWD/services/purchase_orders || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

echo "This process takes 10mins to complete"
echo "Creating GSIs to get by distributor_id and order_date, pack_date or ship_date"
python $PWD/deployment_scripts/9_BREWAPI_102/create_multiple_gsi.py $REGION $STAGE