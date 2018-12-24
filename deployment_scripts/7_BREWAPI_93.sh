REGION=$1
STAGE=$2

# Create tables
echo "Creating tables in dynamodb"
python $PWD/data_dynamodb/create_tables.py $REGION $STAGE

if [ $? != 0 ]; then
    echo "Create tables failed. Exiting."
    exit 1
fi

# Deploy services
echo "Deploy merchandise service"
cd $PWD/services/merchandise || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi
