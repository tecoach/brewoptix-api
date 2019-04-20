STAGE=$1

echo "Deploy all services"
python deploy_all_services.py --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit
