STAGE=$1

echo "Create deployment table if doesn't exist"
cd $PWD/deployment_scripts/22_BREWAPI_110 || exit
python create_deployment_table.py $STAGE
cd ../..

# this snippet can be used in other scripts to check if already deployed
echo "Check if script number is already added to deployment table"
cd $PWD/deployment_scripts/common || exit
python check_script_number_in_deployment_table.py $STAGE 22
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../..

echo "Add script number to deployment table"
cd $PWD/deployment_scripts/common || exit
python add_script_number_to_deployment_table.py $STAGE 22

if [ $? = 0 ]; then
    echo "Issue id successfully added to deployment table"
else
    echo "Issue already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi

cd ../..
