REGION=$1
STAGE=$2

# deploy tables copier lambda service
cd $PWD/deployment_scripts/8_BREWAPI_97/tables_copier_service || exit
sls deploy -v --stage $STAGE --region $REGION
cd ../../.. || exit

echo "Moving data from distributors (old) to supplier-distributors table (new) and remove old table"
python $PWD/deployment_scripts/8_BREWAPI_97/copy_to_table.py $REGION $STAGE

# remove copier service
cd $PWD/deployment_scripts/8_BREWAPI_97/tables_copier_service || exit
sls remove -v --stage $STAGE --region $REGION
cd ../../.. || exit

## Deploy services
echo "Remove distributors service"
cd $PWD/deployment_scripts/8_BREWAPI_97 || exit
sls remove -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully removed"
else
    echo "Removal failed"
fi

cd ../.. || exit

echo "Deploy supplier-distributors service"
cd $PWD/services/supplier_distributors || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

