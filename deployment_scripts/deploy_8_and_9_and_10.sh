REGION=$1
STAGE=$2

# This script assumes that the current state of the stage
# is before distributors were renamed to supplier-distributors

# !! please run this script from project home directory !!

# checkout commit after new-distributors PR merge
git checkout 9010992a12490d981dcc1a3b294dc510ecfe86c5
sh $PWD/deployment_scripts/8_BREWAPI_97.sh $REGION $STAGE

# checkout master
git checkout master

# deploy new distributors service
echo "Deploy new distributors service"
cd $PWD/services/distributors || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

echo "Deploy purchase-orders service"
cd $PWD/services/purchase_orders || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit

# this script creates a lambda service to copy data between tables (for speed)
# backups tables, deletes original tables, creates with new schema, and copies back all items from backups
sh $PWD/deployment_scripts/10_BREWAPI_107.sh $REGION $STAGE
