STAGE=$1
SCRIPT_NUM=48
# this snippet can be used in other scripts to check if already deployed
echo "Check if script number is already added to deployment table"
cd $PWD/deployment_scripts/common || exit
python check_script_number_in_deployment_table.py $STAGE $SCRIPT_NUM
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

echo "Re-Deploy all services"
python deploy_all_services.py --stage $STAGE

echo "Add script number to deployment table"
cd $PWD/deployment_scripts/common || exit
python add_script_number_to_deployment_table.py $STAGE $SCRIPT_NUM

if [ $? = 0 ]; then
    echo "Script number successfully added to deployment table"
else
    echo "Script number already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi
