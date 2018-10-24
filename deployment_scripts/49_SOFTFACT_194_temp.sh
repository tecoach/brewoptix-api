STAGE=$1
SCRIPT_NUM=49

echo "Script version: 1 (fix: skips copied tables)"

# Create tables
echo "Creating tables in dynamodb"
python $PWD/data_dynamodb/create_tables.py $STAGE

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
