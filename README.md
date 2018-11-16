# brewoptix-web-api
The Serverless Python API for the web application

# Contents
 
[How to Run and Deploy](#How-to-Run-and-Deploy)

[Troubleshooting](#Troubleshooting)

[Implementation](#Implementation)

[Deployment Scripts](#Deployment-Scripts)

[Testing](#Testing)

[cURL statements](#cURL-Statements)

[Next Steps](#Next-Steps)

[Conclusion](#Conclusion)

# How to Run and Deploy

## Pre-requisites

1. NodeJS: Serverless project and its plugins depend upon node. Its good to update node to a latest stable version.

I use `nvm` to install and maintain multiple `npm` versions. Using `nvm` install `10.15.3 LTS` or above.

2. Docker

Docker is used to download and package python requirements and also for `localstack` which is useful in testing.

3. Serverless framework

With `npm` installed please run `npm install -g serverless`.

This shouldn't fail because of lack of `sudo` access. If it does fail upon a permission error, please install `npm` using `nvm`.
 
4. Rollbar setup:

To add rollbar based logging, please create a rollbar account at: https://rollbar.com. An access_token will be obtained, 
following the below steps, which will go into `config.{stage}.json` file of the output project for field "ROLLBAR_SECRET".

Upon signup, rollbar shows a quick setup wizard, please follow it.

i. Create a project

ii. Choose `python` as the technology

iii. Copy the server-side access token shown. For example a python code such as `rollbar.init('bb851b91918441349439356286ef1b95')` will be shown. 
The text in init is the access token.

To find this token later, upon logging into rollbar, choose project on top left corner, choose settings, copy contents of `post_server_item`

## Installing project dependencies

1. Install Serverless plugin to manage python requirements:

`sls plugin install -n serverless-python-requirements`

2. Create a virtual environment and install python dependencies for local development

```bash
virtualenv -p /usr/bin/python3.6 ~/.virtualenv/prolanceEnv
source ~/.virtualenv/prolanceEnv/bin/activate
pip install -r requirements-dev.txt
```

3. Setup AWS Credentials:

Install the AWS CLI interface (Ref: https://docs.aws.amazon.com/cli/latest/userguide/awscli-install-bundle.html)

```bash
pip3 install awscli --upgrade --user
```

and run the following commands

```bash
aws configure
```

You can enter `AWS_ACCESS_ID`, `AWS_ACCESS_SECRET` and `region-name` of an admin user account. 
Pls note, the policies and access permissions of this user has nothing to do with the policies attached to lambda functions.

Lambda functions can have policies attached which defines the resources that each function have access to and events that can trigger them.
These policies are defined in `serverless.yml` along with other configuration.

4. Also install pseudo-parameters plugin which gives easy access to AWS Cloudformation variables like {AWS::AccountId}

`sls plugin install -n serverless-pseudo-parameters`

5. Install `sls plugin install -n serverless-prune-plugin`

This plugin helps purge previous versions of functions from AWS

## Create Dynamodb Tables

```bash
python data_dynamodb/create_tables.py us-east-1 prod
```

This creates all the tables in dynamodb in `us-east-1` AWS region, for stage `prod`. You can change the `us-east-1` argument if required.

Please note: this creates tables in both Dynamodb and Aurora. Please make sure `config.{stage}.json` has the `AURORA_*` key-val pairs in them.
Check `config.example.json` for more details.

## Create Aurora Tables

To create an Aurora Serverless database instance (for inventory API), please go to AWS Web Console > Aurora ( https://console.aws.amazon.com/rds/home?region=us-east-1 )
and click on `Create Database`

We are going to manually setup the database cluster instance and create a database inside it:

1. Click on `Create Database` and make the following choices under Engine Options:
    Engine: `Amazon Aurora`, 
    Edition: `Amazon Aurora with MySQL compatibility`, 
    Version: `Aurora (MySQL)-5.6.10a` (or latest)
    Database Location: `Regional` (for development. `Global` deploys to all locations)
    
2. Database Features: 
    Choose `Serverless` as we get to configure the Aurora scaling resources

3. Settings:
    a. Database cluster name: Pls name it `brewoptix-{stage}`
    b. Set a master username and password. Please choose a secure password and save a copy to be added to AWS secrets manager later

4. Leave Capacity settings as it is (min: 1, max: 64)

5. Connectivity:

    Use the default VPC settings and go ahead to the next step.
    
(Aurora lives inside a VPC and we need to configure our serverless application to have access to this VPC to interact with the database.)

6. Please make sure `Data API` is enabled and click on `Create Database`. Wait for the database to launch. 

If the `create database` action fails with any error, please fix it.

Troubleshooting:
 1. Not enough subnets in the VPC. To fix this, please ensure that there are atleast 2 subnets in different Availability Zones under the VPC

7. Setup a secret in AWS Secret Manager:
    a. Go to AWS > AWS Secrets manager and click on `Create Secret`
    b. Choose `Credentials for RDS `
    c. Specify the `username` and `password` selected for the database above
    d. Choose the db instance `brewoptix-{stage}` below and click Next
    e. Name the secret `brewoptix-{stage}-secret` and click next.
    f. Click next again, and click on `Store`
    
8. Config JSON:
    a. Go to AWS Secrets > select `brewoptix-{stage}-secret` and under secure details, pls copy value under `Secret ARN` and
    paste this against key `AURORA_DB_SECRET_ARN` in `config.{stage}.json`
    b. Go to AWS RDS > Databases > select `brewoptix-{stage}` and under Configuration tab, pls copy value under `ARN` and
    paste this against key `AURORA_DB_ARN` in `config.{stage}.json`

9. Create a database in the db instance:
    a. Go to AWS RDS and Click on `Query Editor`
    b. Select instance `brewoptix-{stage}` and enter the `username` and `password` to connect to it and click on `connect to database`
    c. Once in editor, please create a new database using the command:
    `CREATE DATABASE brewoptixdb;`
    d. You can execute `SHOW DATABASES;` to check if the database was created

Please note: we need to run `create_tables.py` for reporting APIs to work.

## Insert object into Aurora table

The following python snippet can be used to insert an object into Inventory table. Please run it from `brewoptix-web-api` parent dir.

```python
from data_dynamodb.aurora_adapter import AuroraStorage
import uuid
import json

stage = "test"    # please set stage here

config_filename = 'config.' + stage + '.json'

with open(config_filename, 'r') as fp:
    config = json.load(fp)
    
db_arn = config["AURORA_DB_ARN"]
db_secret_arn = config["AURORA_DB_SECRET_ARN"]
db_name = config["AURORA_DB_NAME"]

rds = AuroraStorage(db_arn,
db_secret_arn,  
db_name)

table = "inventory"

obj = {
    "product_id": str(uuid.uuid4()),
    "brand_id": str(uuid.uuid4()),
    "package_type_id": str(uuid.uuid4()),
    "created_on": "2019-08-12",
    "on_hand": 25,
    "produced": 25,
    "sales": 10,
    "adjustment": 15,
    "on_hand_end": 12
}

# Add a row in table
rds.save(table, obj)
```
## Setup CloudFront for Brands Logos s3 bucket

1. Open the [CloudFront console](https://console.aws.amazon.com/cloudfront).
2. Choose Create Distribution.
3. Under Web, choose Get Started.
4. For Origin Domain Name, you can choose your S3 bucket's REST API endpoint from the drop-down menu. Please refer to the BucketName from `config.{stage}.json` and choose
`{BUCKET_NAME}.s3.amazonaws.com`
5. For Viewer Protocol Policy, choose HTTP and HTTPS.
Note: Choosing HTTPS Only blocks all HTTP requests.
6. Click on `create distribution`

Once the cloudfront distribution is created, all the S3 objects can be accessed through cloudfront endpoint. For example,
an object `https://test-brand-logos.s3.amazonaws.com/ad51d5ac-17bb-4240-8648-c483b224b2aa/brands/b60186cb-e734-41b6-8a37-5971d6ee7a2c/logo.png`
can be accessed at `https://d2reh2o9rhehzl.cloudfront.net/ad51d5ac-17bb-4240-8648-c483b224b2aa/brands/b60186cb-e734-41b6-8a37-5971d6ee7a2c/logo.png`
where `d2reh2o9rhehzl.cloudfront.net` is the cloudfront domain name

## Local Development environment setup

This section discusses how to setup a local environment. Please make sure to read the sub-section "Limitations".

### First time setup

1. To deploy the api locally, there are a few requirements that needs to be installed.

A. Please make sure `docker` is installed in your computer. Please follow docker's official installation instructions to install docker.

B. From the project parent directory run,
```
npm install --save-dev serverless-plugin-scripts
npm install --save-dev serverless-offline-python
```

C. Please install `localstack` using pip

```
pip install localstack
```

2. Create `config.local.json` where `local` is a stage exclusive for local development.

Please refer to the section [Configuring Deployment](#Configuring-Deployment) to understand the different config variables that need to be set in `config.local.json`.

Please note that the Auth0 variables are of a live Auth0 environment. The current purpose of Local development setup is to reduce the deploy time and to reduce costs.

All variables in `config.example.json` other that `AURORA_*` type variables needs to be populated in `config.local.json`

3. We can use `sls localize` command to setup dynamodb locally (using `dynamodb-local`) and create tables in it.

`sls localize`

This command runs scripts from `dynamodb_local_scripts` to setup dynamodb_local and export environment variables.
`dynamodb_local_config.sh` can be edited if you wish to change ports assigned to `dynamodb_local` or change `docker` container name etc.

This command also runs `sls offline` and starts serving the APIs locally at port 3000 by default.

4. You can use `dynamodb-admin` to visualize the tables. [Dynamo-Admin](https://github.com/aaronshaf/dynamodb-admin)

In a new terminal session, you can install and run `dynamodb-admin` using commands:

```
npm install dynamodb-admin -g
dynamodb-admin
```

### Running project locally

After the first time setup, the only commands that needs to be run to deploy project locally is:

1. Open a terminal session and start localstack

```
localstack start
```

Wait for all services to be Ready.

2. In a new terminal session run:

```
sls localize
```

This will run the APIs at endpoint http://localhost:3000 as the base URL. Please use Curl or Postman to work with the lambdas.
There is no Hot reloading available. Please `Ctrl+C` and re-run `sls localize` upon making changes to the Repo methods or Handlers.

### Limitations and Future changes

1. RDS is not available locally. So RDS specific APIs like `inventory` cannot be tested.
2. `local_stack.json` has the local stack resources that needs to be provisioned. It is provisioned by `dynamodb_local_scripts/create_localstack_resources.py`
In future improvements, events like "SNS publish to add items to SQS", "Availability of messages in SQS to run process queue handlers (e.g. process_projections)" needs to be updated
3. Dynamodb-local at present doesn't persist data, so upon a computer restart, all dynamo tables will be provisioned empty again.
If you would like to use throwaway emails, please consider using 10minutemail.net to create disposable email ids.

Future: data persistence can be brought about in dynamodb-local.


# Configuring Deployment
=========================

Before deploying, a config file with secrets like the AUTH0_CLIENT_ID, can be created, which will be used to set Runtime OS environment variables used by the lambda functions.

If the deployment stage is `dev` create a config file named `config.dev.json` in the project's parent folder.

This is an example content of the JSON file:

```json
{
  "REGION": "us-east-1",
  "AUTH0_CLIENT_ID": "ThABFIgh99ZideKcy-1WmNC8E6Js5Rn4",
  "AUTH0_CLIENT_SECRET": "hiY3oPJSO-ax5OtXjnbFiaNaup479qGWhTURwxCUNAukX3naPGutOTITpI4vUJV_",
  "AUTH0_MANAGEMENT_API_CLIENT_ID": "bfkODTJWm3O37eEokHzSChnQzu6gbkcS",
  "AUTH0_MANAGEMENT_API_CLIENT_SECRET": "ZiYd8fjhKl0MboUpK6BRwx0qcDKN9WS99Ab06_EKP3ABgrZRNMXUZxOn0Sf5BGvY",
  "AUTH0_AUDIENCE": "https://neotheicebird.auth0.com/api/v2/",
  "AUTH0_DOMAIN": "https://neotheicebird.auth0.com",
  "AUTH0_CONNECTION": "Username-Password-Authentication",
  "USERS_MASTER_PASSWORD": "ABCD!@#$1234",
  "SIGNUP_ORIGIN_URL": "*",
  "UPWORK_REQUEST_RETRIES": 2
}
```

`AUTH0_CLIENT_ID` and `AUTH0_CLIENT_SECRET` are found under `Applications > testfdc01` in our Apps' `settings` tab.
`AUTH0_MANAGEMENT_API_CLIENT_ID` and `AUTH0_MANAGEMENT_API_CLIENT_SECRET` are found under `Applications > testfdc01-management` in our Apps' `settings` tab.
`REGION` refers to `dynamodb` and `lambda` AWS region.
`USERS_MASTER_PASSWORD` is a secret that is used to generate Auth0 user profiles' passwords upon signup. If this info is lost or changed, exisiting users might have to go through a reset password flow (NotImplementedYet) to get access to prolance again.
`SIGNUP_ORIGIN_URL` is the URI from which `POST /signup` originates. If it is set to any value other than "*", the handler checks if the request originates from the same domain and raises error if not.

## Deploy Serverless Application to AWS

Prolance consists of multiple services, and they can be deployed all at once using the following command:

```bash
# For Dev or Staging or Test environments
python deploy_all_services.py --stage {stage}
```
The configuration of any stage can be done to the file `config.{STAGE}.json`. Please refer to the section [Configuring Deployment](#Configuring Deployment) for more details on how to configure a stage.

If you wish to deploy to production, we can set the AWS_PROFILE environment variable

```bash
AWS_PROFILE=PRODUCTION_PROFILE_NAME python deploy_all_services.py --stage prod
```

The above command takes some time to complete and always deploys all the services starting with the Auth API.

If changes were made only to one or few services, then they can be individually updated using the following command:

```bash
sls deploy -v --stage dev
```

Or for Production deployment

```bash
AWS_PROFILE=PRODUCTION_PROFILE_NAME sls deploy -v --stage prod
```

Pls note, adding environment variable `AWS_PROFILE` can help us choose the AWS Profile using which we deploy. This can help us deploy to multiple AWS Accounts.
Please ignore the AWS_PROFILE part if not required.

Configure Authentication and Authorization
===========================================

1. Create an Auth0 account at auth0.com

2. While signing up, we would be creating a domain (e.g. `brewoptixdev01.auth0.com`)

3. Under `Applications` to create new app, click on `Create Application` and give it a name (`brewoptixdev01`). Select `Single Page Web Application`.

4. Under the current app's `settings` tab, scroll down and click on `Show Advanced settings` and click on `Certificates` to get the public key with which the serverless service is going to sign the tokens.
Copy the contents on signing `Signing Certificate` and paste in a local file named `public_key` in the `brewoptix-web-api` folder.

5. Click on `Grant Types` and check `Password`, uncheck all the other grant types and save changes.

6. To configure the database to be used, click on `Connections > Database` and click on the default database `Username-Password-Authentication`. 
a. Settings like min and max password length, password policy, can be configured here.
b. Under applications tab we should see `brewoptixdev01` enabled, if not please `enable` application.
c. clicking `Try connection` should work with a login screen.

7. To make password grant work, we have to set `Default Audience` and `Default Directory`, to do that:

a. Go to account settings (top right under your username)
b. On the general tab scroll down to the API Authorization Settings section
c. Default Audience would be your API identifier. This can be found under `APIs > Auth0 Management API`. `API Audience` is the identifier (`https://brewoptixdev01.auth0.com/api/v2/`)
d. Default Directory would be your connection such as database connection name (`Username-Password-Authentication`)
e. Paste values and save.
Ref: https://stackoverflow.com/questions/41626602/how-to-make-a-username-password-request-with-auth0-custom-api-getting-error-un

8. CORS URLs: Under `Applications > brewoptixdev01 > Settings` scroll down to `Allowed Origins (CORS)` and enter any valid URL from which Auth0 endpoints are accessed (`http://localhost:8080/signin`).

Allowed Origins are URLs that will be allowed to make requests from JavaScript to Auth0 API (typically used with CORS). By default, all your callback URLs will be allowed.

Leave it empty, if you are in development.

9. To enable users ability to create/delete their accounts, we need to setup another application which is a machine-to-machine application. To do that:
 a. Click on applications and create a new application
 b. Name it (`brewoptixdev01-management`), select application type to be `machine-to-machine`, select `Auth0 API` and add scopes. Required scopes are `update:users, delete:users, create:users, read:users`.

# Troubleshooting

1. `Missing required key 'Bucket' in params` error appears while deploying

Please make sure nodejs installed is updated to the latest stable version. Currently it is `10.15.3`.
Update `npm` to latest version. Update `serverless` using `npm install -g serverless`.

If the above steps do not work, and you had deployed the application in the past, then try deleting corresponding stacks from AWS Cloudformation.
 
2. Installing serverless plugins (npm global packages) asks for admin permissions.

While adding `sudo` to the plugin install command could solve this, it could lead to other issues. The best way to solve
this would be to install `nvm` and then install `npm` using `nvm`. `nvm` maintains global packages in `home` directory and wouldn't need 
elevated permissions.

3. `Client has not been granted scopes: create:users`

Please check if the `machine-to-machine` application has right scope attached. To do that, Go to your Auth0 account,
a. Navigate to `APIs` > `Auth0 management API`> `Machine to Machine Applications`
b. Click on the right arrow next to the App, whose `client_id` is in the config
c. Add required scopes and click `Update`.
Required scopes are `update:users, delete:users, create:users, read:users`

# Design

# Implementation

Most of the code so far is reused from the FDC Project. Some changes had to be made to make development easier, and also to adjust to latest changes in the dependencies.
Some of the differences with FDC:

1. Prolance webapi uses `serverless-python-offline` like FDC, but unlike FDC, this project uses`dynamodb-local` to setup and write to a locally deployed dynamodb, so that while development, the writes and reads are more disposable, and we don't need to write to cloud dynamodb.

2. FDC uses `cryptography` and `PyJWT` to achieve JWT decoding and verification (Please refer to `services/auth.py`), But we are now facing issues of `cryptography` library making
breaking changes such as not releasing cpython 36 wheels, which is required by Amazon Linux to install `cryptography`. Even though that can be solved by building from source,
another issue is that `cryptography` lib is dependant on `openssl` to parse certificates issued by Auth0, but the openssl version in Amazon Linux is old and is deprecated on `cryptography` library,
this leads to an `unable to open certificate` issue

For this reason, the JWT code is changed using `python_jose` for jwt operations and `pycryptodome` for crypto related operations. This solves the issues faced above.

# Testing

**Oct-2-2019: Please Note, Local server has issues that need to be fixed. So testing might also fail**

The APIs are unit tested using `pytest` and `dynamodb_local`. The tests can be found in `/tests` directory.
To run tests, we need to:

1. Initialize `dynamodb_local`. To do that run the following command:

`sls localize`

2. To run the unit tests, In a new shell window, please run:

`python -m pytest tests/test_schedules.py`

The argument `tests/test_schedules.py` can be replaced with test modules of other APIs.

# Deployment Scripts

Deployment scripts update an environment like a production environment non-destructively. For example,
`deployment_scripts/1-BREWAPI-73.py` updates Aurora database tables adding a new field `entity_id` and re-populating all data

## 1-BREWAPI-73 - Adding `entity_id` field to Production and Adjustments Aurora Tables.

This script moves `adjustments` and `production` table to a newer schema with `entity_id` in them. It goes through dynamodb tables,
and re-populates reporting tables.

To run the deployment script, from `brewoptix-web-api` please run:

`AWS_PROFILE=profile python deployment_scripts/1-BREWAPI-73.py us-east-1 test`

Where the positional arguments are `REGION` and `STAGE`

There might be some items in dynamodb that fails to get processed and added to aurora,
mostly because they do not have required key-val pairs.
For example, some entities in dynamodb added long back to adjustments table may not have `brand_id` if the tables were not cleared up.
Such items are logged as failures to `deployment_scripts/logs/1-BREWAPI-73-{TIMESTAMP}.txt`

If there is even one failed migration item, the tables are reverted back to their original state before running the script.
These items might have to be manually updated, to get the script run successfully.

The failed items are logged to `deployment_scripts/logs/1_BREWAPI_73_{TIMESTAMP}.txt`

## 2-BREWAPI-86 - Creates new GSI in OnHand and deletes existing GSI

on-hand table has `by_supplier_id_and_product_id` which is an old index. This has to be removed and a new index `by_supplier_id` has to be added. This script does that.

To run this script, please use the command:

`AWS_PROFILE=profile python deployment_scripts/2-BREWAPI-86.py us-east-1 test`

Where the positional arguments are `REGION` and `STAGE`

## 3-BREWAPI-87 - Modifies sales table schema. Replaces `order_number` with `entity_id`

sales aurora table has `order_number` as an attribute and part of natural key. This creates issues with maintaining uniqueness of entries.
This is being replaced by `entity_id` from `purchase-orders` dynamo table.

This script does the following:
1. Backup existing sales table
2. Creates sales table with new schema
3. reprocesses dynamo records and creates entries in sales table (with 3 second delay for projection processing between each record)
4. If successfully done, deletes backup table
5. Else, restores sales to original state. In case of failure, please refer to `deployment_scripts/logs` for files named like `3_BREWAPI_87_{timestamp}.txt`
to find dynamo records that couldn't be processed. These records would have to be manually altered for the script to pass

To run this script, please use the command:

`AWS_PROFILE=profile python deployment_scripts/3_BREWAPI_87.py us-east-1 test`

Where the positional arguments are `REGION` and `STAGE`

## 4-BREWAPI-91 - Adds index `by_supplier_id_and_entity_id` to SQL tables 'production' and 'adjustments'

1. Adds index to tables
2. deploys services and q_services

To run this script, please use the command:

`AWS_PROFILE=profile python deployment_scripts/4_BREWAPI_91.py us-east-1 test`

Where the positional arguments are `REGION` and `STAGE`

## 5-BREWAPI-90 - Modifies primary keys of tables 'sales', 'production' and 'adjustments'

Primary keys of all 3 tables are made ("entity_id", "brand_id", "package_type_id")

To run this script, please use the command:

`AWS_PROFILE=profile python deployment_scripts/5_BREWAPI_90.py us-east-1 test`

Where the positional arguments are `REGION` and `STAGE`

## 6-BREWAPI-90 - Removes `on_hand` sns topic and creates new `on_hand`, `projections` topic

To run this script, please use the command:

`AWS_PROFILE=profile python deployment_scripts/6_BREWAPI_84.py us-east-1 test`

Where the positional arguments are `REGION` and `STAGE`

# cURL Statements

Test environment Base URL: https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test

## Signup

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/signup \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
	"email": "qfp19637@bcaoo.com",
	"password": "SuperSecret123!"
}'
```

## Login

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/login \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
  "username": "qfp19637@bcaoo.com",
  "password": "SuperSecret123!"
}'
```

## Reset password

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/password-reset \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
	"email": "b3797012@urhen.com"
}'
```

## Profile API

Get Profile

```curl
curl -X GET \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/users \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'
```

Update Profile

```curl
curl -X PUT \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/users \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json'
  -d '{
    "marketplaces": [
        {
            "name": "codementor",
            "profile_url": "www.codementor.io/prashanthx","enabled": true,
            "picture": false,
            "skills": false,
            "focus": true,
            "pricing": false
        },
        {
            "name": "upwork",
            "profile_url": "www.upwork.com/prashanthg","enabled": false,
            "picture": false,
            "skills": false,
            "focus": false,
            "pricing": false
        }
    ],
    "lastname": "User",
    "firstname": "Test",
    "user_id": "5d0810c271deea0dd14ce5a6",
    "email": "ocw69080@onqus.com",
    "affiliate_id": "XNBQFO",
    "timezone_name": "utc",
    "timezone_utc_offset": 0,
    "workday_start_time": "09:00",
    "entity_id": "5d0810c271deea0dd14ce5a6",
    "version": "2adbe6c6-0b10-4610-b119-223c7250d601",
    "changed_on": "2019-06-06T08:41:06Z"
}'
```

Delete Profile

```curl
curl -X DELETE \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/users \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'
```

## Supplier API

Get all suppliers

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test//suppliers \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Create Supplier

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/suppliers \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "name": "United Spirits",
    "street1": "MG Road",
    "street2": "india",
    "city": "banglore",
    "state": "karnataka",
    "zip": "600001",
    "phone": "1234567890",
    "website": "www.spirits.com",
    "main_contact_id": "ad51d5ac-17bb-4240-8648-c483b224b2aa",
    "users": []
}'
```

Update Supplier

```curl
curl -X PUT \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/suppliers \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "name": "United Spirits",
    "street1": "MG Road",
    "street2": "india",
    "city": "banglore",
    "state": "karnataka",
    "zip": "600021",
    "phone": "9876543210",
    "website": "www.spirits.com",
    "main_contact_id": "ad51d5ac-17bb-4240-8648-c483b224b2aa",
    "users": [],
    "user_id": "5d081df871deea0dd14ce63a",
    "entity_id": "53142b41-0963-4463-b793-68796f5bc130",
    "version": "2e9498f5-a1a3-478a-a55e-c250c4bce318",
    "changed_on": "2019-06-20T02:55:04Z"
}'
```

Get supplier by Id

```curl
curl -X GET \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/suppliers/5c516c03-2bb8-434b-9041-171eda2c5196 \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'
```

Delete supplier by Id

```curl
curl -X DELETE \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/suppliers/53142b41-0963-4463-b793-68796f5bc130 \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'
```

## Brands API

Get all brands

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test//brands \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Add brand

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/brands \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "name": "Carlsberg",
    "supplier_id": "ad51d5ac-17bb-4240-8648-c483b224b2aa"
}'
```

Update brand

```curl
curl -X PUT \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/brands \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "name": "Carlsberg Soda",
    "supplier_id": "ad51d5ac-17bb-4240-8648-c483b224b2aa",
	"user_id": "5d081df871deea0dd14ce63a",
    "entity_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "version": "f530fce8-ab37-4c08-a726-8ab7b84efb1c",
    "changed_on": "2019-06-20T03:51:58Z"
}'
```

Get brand by id

```curl
curl -X GET \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/brands/2f15bd37-fb8f-457c-9296-bfac03e36745 \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'
```

Delete brand by id

```curl
curl -X DELETE \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/brands/2f15bd37-fb8f-457c-9296-bfac03e36745 \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'  
```

## Package Type API

Get all package types

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test//package-types \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Add Package Type

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/package-types \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "vessel": "can",
    "volume_quantity": 1.0,
    "volume_uom": "gallon",
    "volume_uom_abbr": "gal",
    "volume_in_liters": 3.78541,
    "public": true,
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745"
}
'
```

Update Package Type

```curl
curl -X PUT \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/package-types \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "vessel": "can",
    "volume_quantity": 2,
    "volume_uom": "gallon",
    "volume_uom_abbr": "gal",
    "volume_in_liters": 7.57082,
    "public": false,
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "user_id": "5d081df871deea0dd14ce63a",
    "entity_id": "581fa2a2-631d-4ec4-83a7-c905859681ec",
    "version": "486fccaa-c7c2-43c9-824d-3464f315ed9e",
    "changed_on": "2019-06-20T05:46:46Z"
}'
```

Get Package type by id

```curl
curl -X GET \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/package-types/581fa2a2-631d-4ec4-83a7-c905859681ec \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'
```

Delete Package type by id

```curl
curl -X DELETE \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/package-types/581fa2a2-631d-4ec4-83a7-c905859681ec \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIwVDAyOjAxOjQxLjQ4OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MDk5NjEwMSwiZXhwIjoxNTYxMDMyMTAxfQ.yIFiTG4Sq3uTgiBlsFHAzmCy-8pPs1ODZfG_AN0ZP_WOimitUFeNnqoP7s1KrCjpIJOiZhbhmKXE0Jy4DsTeAj_mT9LlS-W4muvEfQm_MX2XL70aCFHA2ws_IVN-OzCNVZmhNGVCAtIsFMNBOKaAnD7CitiI8kmOii1p5NVrY5A5HYm9aV7odp3lmJKQmTOVbxq0zuQ9E_8tPChdvysv1_TsBiSz_sdMLpg7Iq-nhyiOd1Eg4oiBoEAS7NgmVIxcdzBv3jc3zZOvVFsJdjdbWQzC4UtspaQFOl3VSfCZ3_KxnZJsvtk9P9CkOnAyHZKFFrQIUjT2sXExzKTKAAOaVw' \
  -H 'cache-control: no-cache'
```

## Product API

Get all products

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/products \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Add Product

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/products \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIxVDExOjAwOjExLjE0OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTExNDgxMSwiZXhwIjoxNTYxMTUwODExfQ.Mj5OvYXaLkZ3oH0FHpUPa01TAwKucWfdljfD0EN_cFchM6AzZJg10TXn80CWtKcQIl6yBBBOQbRtY8IYII_85Dcyi7JfZlTFjGZY7UKFPppJNaFeJEtZBYejcs-dlAOoAfF-RNPXxjBm1X58-coYHwvvAsGC_3h-_nPAIoBHFmghZjVwpSEoiSM_SY6kpXs5xacoFkc29WfVqYElIaqW787UkSygiGG_uwHm4zjGKmc5zK0lJudFay4SXSqMQ5ZzhD9Xqe9G0vxwNS9eKX4aC0kDPw6uHpeXHwn0Ut3Li-lPW9Lo0DkPNJer_t49C8pIHZ-RyTmuMIjuhz-XTYIXtA' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "package_id": "581fa2a2-631d-4ec4-83a7-c905859681ec",
    "brand_id": "60701b3a-6aca-40cf-95ae-03eab68c23e0"
}
'
```

Update Product

```curl
curl -X PUT \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/products \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIxVDExOjAwOjExLjE0OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTExNDgxMSwiZXhwIjoxNTYxMTUwODExfQ.Mj5OvYXaLkZ3oH0FHpUPa01TAwKucWfdljfD0EN_cFchM6AzZJg10TXn80CWtKcQIl6yBBBOQbRtY8IYII_85Dcyi7JfZlTFjGZY7UKFPppJNaFeJEtZBYejcs-dlAOoAfF-RNPXxjBm1X58-coYHwvvAsGC_3h-_nPAIoBHFmghZjVwpSEoiSM_SY6kpXs5xacoFkc29WfVqYElIaqW787UkSygiGG_uwHm4zjGKmc5zK0lJudFay4SXSqMQ5ZzhD9Xqe9G0vxwNS9eKX4aC0kDPw6uHpeXHwn0Ut3Li-lPW9Lo0DkPNJer_t49C8pIHZ-RyTmuMIjuhz-XTYIXtA' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "package_id": "581fa2a2-631d-4ec4-83a7-c905859681ec",
    "brand_id": "ef65defc-c6ef-47d4-add9-2c988ca1ba07",
    "user_id": "5d081df871deea0dd14ce63a",
    "entity_id": "b2532407-b63a-4e83-a7dd-a150fcc29b73",
    "version": "df65defc-c6ef-47d4-add9-2c988ca1ba07",
    "changed_on": "2019-06-21T11:00:41Z"
}'
```

Get product by id

```curl
curl -X GET \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/products/b2532407-b63a-4e83-a7dd-a150fcc29b73 \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIxVDExOjAwOjExLjE0OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTExNDgxMSwiZXhwIjoxNTYxMTUwODExfQ.Mj5OvYXaLkZ3oH0FHpUPa01TAwKucWfdljfD0EN_cFchM6AzZJg10TXn80CWtKcQIl6yBBBOQbRtY8IYII_85Dcyi7JfZlTFjGZY7UKFPppJNaFeJEtZBYejcs-dlAOoAfF-RNPXxjBm1X58-coYHwvvAsGC_3h-_nPAIoBHFmghZjVwpSEoiSM_SY6kpXs5xacoFkc29WfVqYElIaqW787UkSygiGG_uwHm4zjGKmc5zK0lJudFay4SXSqMQ5ZzhD9Xqe9G0vxwNS9eKX4aC0kDPw6uHpeXHwn0Ut3Li-lPW9Lo0DkPNJer_t49C8pIHZ-RyTmuMIjuhz-XTYIXtA' \
  -H 'cache-control: no-cache'
```

Delete product by id

```curl
curl -X DELETE \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/products/858f112c-a7c0-4693-81db-7c3c8fa6e0ec \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTIxVDExOjAwOjExLjE0OVoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTExNDgxMSwiZXhwIjoxNTYxMTUwODExfQ.Mj5OvYXaLkZ3oH0FHpUPa01TAwKucWfdljfD0EN_cFchM6AzZJg10TXn80CWtKcQIl6yBBBOQbRtY8IYII_85Dcyi7JfZlTFjGZY7UKFPppJNaFeJEtZBYejcs-dlAOoAfF-RNPXxjBm1X58-coYHwvvAsGC_3h-_nPAIoBHFmghZjVwpSEoiSM_SY6kpXs5xacoFkc29WfVqYElIaqW787UkSygiGG_uwHm4zjGKmc5zK0lJudFay4SXSqMQ5ZzhD9Xqe9G0vxwNS9eKX4aC0kDPw6uHpeXHwn0Ut3Li-lPW9Lo0DkPNJer_t49C8pIHZ-RyTmuMIjuhz-XTYIXtA' \
  -H 'cache-control: no-cache'
```

## OnHand API

Get all on-hand

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/on-hand \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Add OnHand inventory record

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/on-hand \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "product_id": "581fa2a2-631d-4ec4-83a7-c905859681ec",
    "quantity": 25,
    "observation_date": "2018-12-01",
    "actual": true
}
'
```

Update Onhand inventory record

```curl
curl -X PUT \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/on-hand \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "quantity": 30,
    "observation_date": "2019-11-01",
    "actual": false,
    "user_id": "5d081df871deea0dd14ce63a",
    "entity_id": "5ac5d0b6-310f-4fc2-a583-d1c23f08a93d",
    "version": "1c54029f-7f97-4cc9-af84-92f46efa5b47",
    "changed_on": "2019-06-25T23:01:11Z"
}'
```

Get OnHand item by id

```curl
curl -X GET \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/on-hand/9d3042fe-2625-434e-9d29-03ac8f04b982 \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache'
```

Delete OnHand item by id

```curl
curl -X DELETE \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/test/on-hand/5ac5d0b6-310f-4fc2-a583-d1c23f08a93d \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache'
```

## Adjustment API

Get all adjustments

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/adjustments \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Add Adjustment inventory record

```curl
curl -X POST \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/adjustments \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "product_id": "581fa2a2-631d-4ec4-83a7-c905859681ec",
    "quantity": 25,
    "adjustment_date": "22-12-2019",
    "adjustment_type": "lower",
    "notes": "Notes"
}
'
```

Update Onhand inventory record

```curl
curl -X PUT \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/adjustments \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
    "supplier_id": "2f15bd37-fb8f-457c-9296-bfac03e36745",
    "quantity": 30,
    "adjustment_date": "2019-12-21",
    "adjustment_type": "upper",
    "notes": "New notes",
    "user_id": "5d081df871deea0dd14ce63a",
    "entity_id": "44e683c6-b377-4e68-9d12-4117cd964a04",
    "version": "d258032a-7de8-43be-8a89-0d7090cbce37",
    "changed_on": "2019-06-26T00:37:05Z"
}'
```

Get OnHand item by id

```curl
curl -X GET \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/adjustments/44e683c6-b377-4e68-9d12-4117cd964a04 \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache'
```

Delete OnHand item by id

```curl
curl -X DELETE \
  https://hvyqxor7te.execute-api.us-east-1.amazonaws.com/adjustments/858f112c-a7c0-4693-81db-7c3c8fa6e0ec \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6InFmcDE5NjM3IiwibmFtZSI6InFmcDE5NjM3QGJjYW9vLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9mYmQ3ZDEwNDcyMTM4ZGI2YmRlNGIyMjdkOTMwN2JlMD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRnFmLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA2LTI1VDIyOjQ0OjIzLjM4MFoiLCJlbWFpbCI6InFmcDE5NjM3QGJjYW9vLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDA4MWRmODcxZGVlYTBkZDE0Y2U2M2EiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2MTUwMjY2MywiZXhwIjoxNTYxNTM4NjYzfQ.kgwxvzPFBL2IyvC50RGHrjIOTDvPMQ0oUVHnvrf__-t7-rI_WRl6lkezq_QQ4t9Kx0Lmqdh8q-UtoRR-gENAwwcMi8ahNATNLhLwI_r0bipqxfDCYag-KBOTMr5JhOtb1SHPC0jny5TVHnGldWWEvN73tMfCtnCY44X21FlJBrrx5QSFKeWyW4ebG0BNzPNOIxsjx-YZnMwX7F0HMIeHtiyRJMQUME8nr8oli7c0Ru8CO5R7tLYlvAR36h7-jR9GvVATQki2PQSIKzV8ge4YMoOlKnQ9opoScaUPRmLwKfoluR1JYkyfd75pT6ZLOKtJAyJ8t6awA3gKmYWfg8G8ww' \
  -H 'cache-control: no-cache'
```

## Containers API

Get all containers

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/containers \
    -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Add container

```curl
curl -X POST \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/containers \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw' \
  -d '{
    "name": "twelve ounce bottle",
    "volume": 0.09375,
    "volume_uom": "gallon",
    "type": "can",
    "global": true,
    "supplier_id": "60701b3a-6aca-40cf-95ae-03eab68c23e0"
}'
```

Update container

```curl
curl -X PUT \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/containers \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw' \
  -d '{
    "name": "six ounce bottle",
    "volume": 0.047,
    "volume_uom": "gallon",
    "type": "can",
    "global": false,
    "supplier_id": "60701b3a-6aca-40cf-95ae-03eab68c23e0",
    "user_id": "5d26bc028fc6c70caaa8fa7d",
    "entity_id": "ed45c672-7875-4fd1-8e04-d5969ae47d33",
    "version": "c335cc6c-ad44-44e9-8a90-9745cf520fb6",
    "changed_on": "2019-07-27T14:20:11Z"
}'
```

Get container by id

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/containers/ed45c672-7875-4fd1-8e04-d5969ae47d33 \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw' \
```

Delete container by id

```curl
curl -X DELETE \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/containers/ed45c672-7875-4fd1-8e04-d5969ae47d33 \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw' \
```

## Retail Packages API

Get all retail packages

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/retail-packages \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Add Retail package

```curl
curl -X POST \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/retail-packages \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw' \
  -d '{
    "name": "six pack",
    "quantity": 6,
    "container_id": "f0b7bdce-34eb-46ee-b3e0-6a627012a320",
    "supplier_id": "60701b3a-6aca-40cf-95ae-03eab68c23e0"
}'
```

Update Retail package

```curl
curl -X PUT \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/retail-packages \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw' \
  -d '{
    "name": "eight pack",
    "quantity": 8,
    "container_id": "f0b7bdce-34eb-46ee-b3e0-6a627012a320",
    "supplier_id": "60701b3a-6aca-40cf-95ae-03eab68c23e0",
    "user_id": "5d26bc028fc6c70caaa8fa7d",
    "entity_id": "9b19b67d-6270-4d41-8c51-f9e2e001f010",
    "version": "68bd0c2e-363c-49d2-b970-12d16b6c5bed",
    "changed_on": "2019-07-27T14:22:01Z"
}'
```

Get retail package by id

```curl
curl -X GET \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/retail-packages/9b19b67d-6270-4d41-8c51-f9e2e001f010 \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

Delete retail package by id

```curl
curl -X DELETE \
  https://vdq41sac1a.execute-api.us-east-1.amazonaws.com/test/retail-packages/9b19b67d-6270-4d41-8c51-f9e2e001f010 \
  -H 'Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlFrSXpSVFkxTlRjMk1ESkVRVFJEUkRFeFF6RTBOekl3T1RnMlF6RkZNalExUWpNMlJFWXdNdyJ9.eyJuaWNrbmFtZSI6ImIzOTgzNzIyIiwibmFtZSI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsInBpY3R1cmUiOiJodHRwczovL3MuZ3JhdmF0YXIuY29tL2F2YXRhci9lNDBiODA0NDNhMjI0ZTEwNGE5MGFhODJlZGJkYWU4OD9zPTQ4MCZyPXBnJmQ9aHR0cHMlM0ElMkYlMkZjZG4uYXV0aDAuY29tJTJGYXZhdGFycyUyRmIzLnBuZyIsInVwZGF0ZWRfYXQiOiIyMDE5LTA3LTI3VDEyOjU1OjA1LjQxOVoiLCJlbWFpbCI6ImIzOTgzNzIyQHVyaGVuLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiaXNzIjoiaHR0cHM6Ly9uZW90aGVpY2ViaXJkLmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw1ZDI2YmMwMjhmYzZjNzBjYWFhOGZhN2QiLCJhdWQiOiJ0N2lvTkdYZmF1Q0U4aFN0Mzk1MU5uUlFWRno0RmNnciIsImlhdCI6MTU2NDIzMjEwNSwiZXhwIjoxNTY0MjY4MTA1fQ.O54I8nueUdd3ZaB3HQDuWjWOqMomKKr2E982tmAxDTzoy56W2r5xCOd9837mdNLj0_Evva9OchbjBjwi0YXQ1BDz0IyEhCEFS_P1YM0RyRpsZqbXJGgMcS6IPz1vbz4-r3wAf9dnmg_RoZbtKHsaNHETrskBhngQUQSA6wUFbK042xGs4xXrvboJ2ssSIp05OZ0nUyePsHc7bD6aKrYrNK0uthAasRduJjgDcc8hw-pC2o5_CGVRLReXStkz9m7bbxtafMXS6iXHT-aYKb5t7yvaR5NoBU_H1S0uU85tM1Eq-8ajP0ufgPNfK94JyQ9fxdkE8DslQ6St2ZRap9Etgw'
```

# Next Steps

# Conclusion


If there are any questions or problems in the future, please contact *Prashanth* at *neotheicebird@gmail.com*
