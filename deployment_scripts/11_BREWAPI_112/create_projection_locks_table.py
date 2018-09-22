import boto3
import time
from botocore.exceptions import ClientError


class ProjectionLocksAurora:
    table_name = "projection_locks"
    table_description = (
        "CREATE TABLE `projection_locks` ("
        "  `brand_id` CHAR(36) NOT NULL,"
        "  `package_type_id` CHAR(36) NOT NULL,"
        "  `request_id` CHAR(36) NOT NULL,"
        "  `timestamp` int(11) NOT NULL,"
        "  PRIMARY KEY (`brand_id`, `package_type_id`)"
        ") ENGINE=InnoDB")


if __name__ == '__main__':
    import sys
    import json
    import os

    args = sys.argv
    if len(args) >= 3:
        region = args[1]
        stage = args[2]

        rds_client = boto3.client('rds-data', region_name=region)
        sql_models = [ProjectionLocksAurora,]

        config_filename = 'config.' + stage + '.json'
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_filepath = os.path.join(parent_dir, config_filename)

        with open(config_filepath, 'r') as fp:
            config = json.load(fp)

        try:
            db_arn = config["AURORA_DB_ARN"]
            db_secret_arn = config["AURORA_DB_SECRET_ARN"]
            db_name = config["AURORA_DB_NAME"]
        except KeyError:
            print("""Missing key-val pairs AURORA_DB_ARN, AURORA_DB_SECRET_ARN and/or AURORA_DB_NAME in {CONFIG}
            Unable to create SQL Tables""".format(CONFIG=config_filename))

        print("Aurora Tables: ")
        for model in sql_models:
            table_name = model.table_name

            for i in range(3):
                try:
                    response = rds_client.execute_statement(
                        secretArn=db_secret_arn,
                        database=db_name,
                        resourceArn=db_arn,
                        sql="""SELECT *
                        FROM information_schema.tables
                        WHERE table_schema = '{DB_NAME}'
                        AND table_name = '{TABLE_NAME}'
                        LIMIT 1;
                        """.format(DB_NAME=db_name, TABLE_NAME=table_name)
                    )
                    break
                except ClientError as ex:
                    print(ex)
                    print("Attempt {0}".format(i))
                    if ex.response['Error']['Code'] == 'BadRequestException':
                        pass  # Assuming Connection Link error
                    else:
                        raise ex

                    time.sleep(30)
            else:
                raise Exception("Mysql Connection Link Failure. Tried 3 times and failed")

            is_table_exists = bool(response.get("records", None))

            if not is_table_exists:
                print('Creating table: ', model.table_name)
                response = rds_client.execute_statement(
                secretArn=db_secret_arn,
                database=db_name,
                resourceArn=db_arn,
                sql=model.table_description
                )

                if hasattr(model, 'indices'):
                    for index in model.indices:
                        print('Creating index in table: ', model.table_name)
                        response = rds_client.execute_statement(
                            secretArn=db_secret_arn,
                            database=db_name,
                            resourceArn=db_arn,
                            sql=index
                        )
    else:
        print("""FAILED: Running dynamodb tables creation script.
                 REGION needs to be passed as a positional argument
                 while running the script""")


