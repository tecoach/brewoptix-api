STAGE=$1

echo "Deploy on_hand service"
cd $PWD/services/on_hand || exit
sls deploy -v --stage $STAGE

if [ $? = 0 ]; then
    echo "Successfully deployed"
else
    echo "Deployment failed"
fi

cd ../.. || exit
