STAGE=$1
SCRIPT_NUM=49
# this snippet can be used in other scripts to check if already deployed
echo "Check if script number is already added to deployment table"
cd $PWD/deployment_scripts/common || exit
python check_script_number_in_deployment_table.py $STAGE $SCRIPT_NUM
if [ $? = 1 ]; then
    echo "Script already run. Exiting..."
    exit 1
fi
cd ../.. || exit

# Create tables
echo "Creating tables in dynamodb"
python $PWD/data_dynamodb/create_tables.py $STAGE

if [ $? != 0 ]; then
    echo "Create tables failed. Exiting."
    exit 1
fi

echo "Re-Deploy all services"
python $PWD/deploy_all_services.py --stage $STAGE

if [ $? != 0 ]; then
    echo "Deploy all services failed. Exiting."
    exit 1
fi

# deploy tables copier lambda service
echo "Deploy tables copier service"
cd $PWD/deployment_scripts/49_SOFTFACT_194/tables_copier_service || exit
sls deploy -v --stage $STAGE
cd ../../.. || exit

# move data from old tables to new
echo "Migrate data from old table to new single table"
python $PWD/deployment_scripts/49_SOFTFACT_194/migrate_data.py $STAGE

# remove copier service
echo "Remove tables copier service"
cd $PWD/deployment_scripts/49_SOFTFACT_194/tables_copier_service || exit
sls remove -v --stage $STAGE
cd ../../.. || exit

echo "Running create_tables to reset autoscaling on single table"
python $PWD/data_dynamodb/create_tables.py $STAGE

echo "Add script number to deployment table"
cd $PWD/deployment_scripts/common || exit
python add_script_number_to_deployment_table.py $STAGE $SCRIPT_NUM

if [ $? = 0 ]; then
    echo "Script number successfully added to deployment table"
else
    echo "Script number already exists or deployment table doesn't exist. Exiting..."
    exit 1
fi
