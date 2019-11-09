STAGE=$1

echo "Deploy distributors service"
cd $PWD/services/distributors || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

echo "Deploy brands service"
cd $PWD/services/brands || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

echo "Deploy q_adjustment service"
cd $PWD/services/q_adjustments || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit