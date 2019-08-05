STAGE=$1

# this snippet can be used in other scripts to check if already deployed
echo "Check if script number is already added to deployment table"
cd $PWD/deployment_scripts/common || exit
python check_script_number_in_deployment_table.py $STAGE 26
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

echo "Deploy email transmitter service"
cd $PWD/services/email_transmitter || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Creating email template on SES."
cd $PWD/deployment_scripts/26_BREWAPI_153 || exit
aws ses create-template --cli-input-json file://template-email.json

if [ $? = 0 ]; then
    echo "Email template successfully created"
else
    echo "Email template creating failed"
    exit 1
fi
cd ../.. || exit

echo "Add script number to deployment table"
cd $PWD/deployment_scripts/common || exit
python add_script_number_to_deployment_table.py $STAGE 26

if [ $? = 0 ]; then
    echo "Script number successfully added to deployment table"
else
    echo "Script number already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi
