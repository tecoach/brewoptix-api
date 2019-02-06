STAGE=$1
SCRIPT_NUM=1

echo "create deployment table"
cd $PWD/deployment_scripts/common || exit
python create_deployment_table.py $STAGE
cd ../.. || exit

. ./bin/activate;

if [ $? != 0 ]
then
    echo "Please run install.sh before deploying";
    exit 1;
fi;

python $PWD/data_dynamodb/create_tables.py $STAGE

echo "Deploying Auth service"
cd $PWD/services || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi
cd .. || exit

echo "Deploying user session service"
cd $PWD/services/user || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Deploying user profile service"
cd $PWD/services/profile || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Updating email template on SES for user registration."
cd $PWD/deployment_scripts/common/user_register_email || exit
python update_template_email.py $STAGE

if [ $? = 0 ]; then
    echo "Email template successfully updated"
else
    echo "Email template updating failed"
    exit 1
fi
cd ../../.. || exit

echo "Updating email template on SES for purchase order"
cd $PWD/deployment_scripts/common/purchase_order_email || exit
python update_template_email.py $STAGE

if [ $? = 0 ]; then
    echo "Email template successfully updated"
else
    echo "Email template updating failed"
    exit 1
fi
cd ../../.. || exit

echo "Updating deployment version"
cd $PWD/deployment_scripts/common || exit
python update_version.py $STAGE $SCRIPT_NUM

if [ $? = 0 ]; then
    echo "Version successfully added to deployment table"
else
    echo "Version already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi