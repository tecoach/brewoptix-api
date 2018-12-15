STAGE=$1
SCRIPT_NUM=50
# this snippet can be used in other scripts to check if already deployed
echo "Checking if system is already deployed"
cd $PWD/deployment_scripts/common || exit
python check_version_not_run.py $STAGE $SCRIPT_NUM
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

echo "Deploy brands service"
cd $PWD/services/brands || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Deploy containers service"
cd $PWD/services/containers || exit
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

echo "Deploy merchandise service"
cd $PWD/services/merchandise || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Deploy package_types service"
cd $PWD/services/package_types || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
    exit 1
fi

cd ../.. || exit

echo "Deploy products service"
cd $PWD/services/products || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
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

echo "Deploy retail_packages service"
cd $PWD/services/retail_packages || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
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

echo "Updating deployment version"
cd $PWD/deployment_scripts/common || exit
python update_version.py $STAGE $SCRIPT_NUM

if [ $? = 0 ]; then
    echo "Version successfully added to deployment table"
else
    echo "Version already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi
