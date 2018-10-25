STAGE=$1
SCRIPT_NUM=51
# this snippet can be used in other scripts to check if already deployed
echo "Checking if system is already deployed"
cd $PWD/deployment_scripts/common || exit
python check_version_not_run.py $STAGE $SCRIPT_NUM
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

python $PWD/deploy_all_services.py --stage $STAGE
if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

echo "Updating deployment version"
cd $PWD/deployment_scripts/common || exit
python update_version.py $STAGE $SCRIPT_NUM

if [ $? = 0 ]; then
    echo "Version successfully added to deployment table"
else
    echo "Version already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi
