REGION=$1
STAGE=$2

# deploy tables copier lambda service
cd $PWD/deployment_scripts/10_BREWAPI_107/tables_copier_service || exit
sls deploy -v --stage $STAGE --region $REGION
cd .. || exit

# create backup tables (pass total segments arg as last argument for parallel copying in dynamodb)
python remove_reserved_keys_convert_tables.py $REGION $STAGE 10

if [ $? != 0 ]; then
    echo "Migrate tables failed. Exiting."
    exit 1
fi

# remove service
cd tables_copier_service || exit
sls remove -v --stage $STAGE --region $REGION

cd ../../..
python deploy_all_services.py --stage $STAGE