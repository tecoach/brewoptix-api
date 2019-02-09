STAGE=$1

echo "Redeploy deployment table"
python deployment_scripts/24_BREWAPI_143/recreate_deployment_table.py $STAGE

if [ $? = 0 ]; then
    echo "Table successfully recreated"
else
    echo "Table update failed"
fi

# this snippet can be used in other scripts to check if already deployed
echo "Check if script number is already added to deployment table"
cd $PWD/deployment_scripts/common || exit
python check_script_number_in_deployment_table.py $STAGE 24
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

echo "Add script number to deployment table"
cd $PWD/deployment_scripts/common || exit
python add_script_number_to_deployment_table.py $STAGE 24

if [ $? = 0 ]; then
    echo "Issue id successfully added to deployment table"
else
    echo "Issue already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi

cd ../.. || exit
