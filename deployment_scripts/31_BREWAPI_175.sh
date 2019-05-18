STAGE=$1

# this snippet can be used in other scripts to check if already deployed
echo "Check if script number is already added to deployment table"
cd $PWD/deployment_scripts/common || exit
python check_script_number_in_deployment_table.py $STAGE 31
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

echo "Updating dynamoDB tables."
cd $PWD/deployment_scripts/31_BREWAPI_175 || exit
python update_dynamodb.py $STAGE

if [ $? = 0 ]; then
    echo "DynamoDB updated successfully."
else
    echo "DynamoDB updating failed"
    exit 1
fi
cd ../.. || exit

echo "Deploy supplier_distributors service"
cd $PWD/services/supplier_distributors || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Deploy distributor_suppliers service"
cd $PWD/services/distributor_suppliers || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Add script number to deployment table"
cd $PWD/deployment_scripts/common || exit
python add_script_number_to_deployment_table.py $STAGE 31

if [ $? = 0 ]; then
    echo "Script number successfully added to deployment table"
else
    echo "Script number already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi
