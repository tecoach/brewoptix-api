STAGE=$1

# this snippet can be used in other scripts to check if already deployed
echo "Check if script number is already added to deployment table"
cd $PWD/deployment_scripts/common || exit
python check_script_number_in_deployment_table.py $STAGE 33
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

echo "Deploy purchase_orders service"
cd $PWD/services/purchase_orders || exit
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
python add_script_number_to_deployment_table.py $STAGE 33

if [ $? = 0 ]; then
    echo "Script number successfully added to deployment table"
else
    echo "Script number already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi
