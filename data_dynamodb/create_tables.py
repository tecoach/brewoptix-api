import boto3
from bloop import (
    BaseModel, Boolean, Column, Number, String,
    UUID, Map, List, GlobalSecondaryIndex, Engine
)
import time
from botocore.exceptions import ClientError
from autoscaling_utils import AutoScaleDynamodb


class Brewoptix(BaseModel):
    class Meta:
        table_name = 'brewoptix-{STAGE}'
        read_units_min = 2
        read_units_max = 20
        write_units_min = 2
        write_units_max = 20
        autoscale_table = True
        autoscale_all_indices = True

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    obj_type = Column(String)
    affiliate_id = Column(String, default='')
    user_id = Column(UUID)
    email = Column(String)

    by_affiliate_id_and_obj_type = GlobalSecondaryIndex(
        projection='all',
        hash_key='affiliate_id',
        range_key='obj_type'
    )

    by_email_and_obj_type = GlobalSecondaryIndex(
        projection='all',
        hash_key='email',
        range_key='obj_type'
    )

    name = Column(String)
    supplier_id = Column(UUID)

    by_name_and_obj_type = GlobalSecondaryIndex(
        projection='all',
        hash_key='name',
        range_key='obj_type'
    )

    by_supplier_id_and_obj_type = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        range_key='obj_type'
    )

    distributor_id = Column(UUID)

    by_distributor_id_and_obj_type = GlobalSecondaryIndex(
        projection='all',
        hash_key='distributor_id',
        range_key='obj_type'
    )

    access_code = Column(String, default='')

    by_access_code_and_obj_type = GlobalSecondaryIndex(
        projection='all',
        hash_key='access_code',
        range_key='obj_type'
    )


class PurchaseOrderNumber(BaseModel):
    class Meta:
        table_name = 'brewoptix-purchase-order-number'
        read_units_min = 2
        read_units_max = 20
        write_units_min = 2
        write_units_max = 20
        autoscale_table = True

    # Api attrs
    supplier_id = Column(UUID, hash_key=True)


class Deployment(BaseModel):
    class Meta:
        table_name = 'brewoptix-deployment'
        read_units = 1
        write_units = 1

    script_number = Column(Number, hash_key=True)


class OnHandAurora:
    table_name = "on_hand"
    table_description = (
        "CREATE TABLE `on_hand` ("
        "  `supplier_id` CHAR(36)  NOT NULL,"
        "  `created_on` DATE NOT NULL,"
        "  `brand_id` CHAR(36) NOT NULL,"
        "  `package_type_id` CHAR(36) NOT NULL,"
        "  `quantity` int(11) NOT NULL,"
        "  `actual` BOOLEAN,"
        "  PRIMARY KEY (`brand_id`, `package_type_id`, `created_on`, `actual`)"
        ") ENGINE=InnoDB")
    indices = [
        "CREATE INDEX by_created_on_and_supplier_id ON on_hand (created_on, supplier_id)",
    ]


class ProductionAurora:
    table_name = "production"
    table_description = (
        "CREATE TABLE `production` ("
        "  `supplier_id` CHAR(36)  NOT NULL,"
        "  `entity_id` CHAR(36)  NOT NULL,"
        "  `production_date` DATE NOT NULL,"
        "  `brand_id` CHAR(36) NOT NULL,"
        "  `package_type_id` CHAR(36) NOT NULL,"
        "  `quantity` int(11) NOT NULL,"
        "  PRIMARY KEY (`entity_id`, `brand_id`, `package_type_id`)"
        ") ENGINE=InnoDB")
    indices = [
        "CREATE INDEX by_entity_id_and_supplier_id ON production (entity_id, supplier_id)",
        "CREATE INDEX by_production_date_and_supplier_id ON production (production_date, supplier_id)",
    ]


class AdjustmentsAurora:
    table_name = "adjustments"
    table_description = (
        "CREATE TABLE `adjustments` ("
        "  `supplier_id` CHAR(36)  NOT NULL,"
        "  `entity_id` CHAR(36)  NOT NULL,"
        "  `adjustment_date` DATE NOT NULL,"
        "  `brand_id` CHAR(36) NOT NULL,"
        "  `package_type_id` CHAR(36) NOT NULL,"
        "  `quantity` int(11) NOT NULL,"
        "  PRIMARY KEY (`entity_id`, `brand_id`, `package_type_id`)"
        ") ENGINE=InnoDB")
    indices = [
        "CREATE INDEX by_entity_id_and_supplier_id ON adjustments (entity_id, supplier_id)",
        "CREATE INDEX by_adjustment_date_and_supplier_id ON adjustments (adjustment_date, supplier_id)",
    ]


class SalesAurora:
    table_name = "sales"
    table_description = (
        "CREATE TABLE `sales` ("
        "  `supplier_id` CHAR(36)  NOT NULL,"
        "  `distributor_id` CHAR(36)  NOT NULL,"
        "  `sale_date` DATE NOT NULL,"
        "  `brand_id` CHAR(36) NOT NULL,"
        "  `package_type_id` CHAR(36) NOT NULL,"
        "  `entity_id` CHAR(36) NOT NULL,"
        "  `quantity` int(11) NOT NULL,"
        "  PRIMARY KEY (`entity_id`, `brand_id`, `package_type_id`)"
        ") ENGINE=InnoDB")
    indices = [
        "CREATE INDEX by_entity_id_and_supplier_id ON sales (entity_id, supplier_id)",
        "CREATE INDEX by_sale_date_and_supplier_id ON sales (sale_date, supplier_id)",
    ]


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

    # for development we use dynamodb-local
    sys.path.insert(0, os.path.join(os.path.abspath(os.path.curdir), 'dynamodb_local_patch.py'))
    from dynamodb_local_patch import patch_engine

    args = sys.argv
    if len(args) >= 2:
        stage = args[1]

        config_filename = 'config.' + stage + '.json'
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_filepath = os.path.join(parent_dir, config_filename)

        with open(config_filepath, 'r') as fp:
            config = json.load(fp)

        region = config['REGION']
        dynamo_target_utilization = config['DYNAMODB_TARGET_UTILIZATION']
        scale_in_cooldown = config['DYNAMODB_SCALE_IN_COOLDOWN_SECS']
        scale_out_cooldown = config['DYNAMODB_SCALE_OUT_COOLDOWN_SECS']

        try:
            endpoint = args[2]
            client = boto3.client('dynamodb', region_name=region, endpoint_url=endpoint)
            engine = patch_engine(Engine(dynamodb=client))
        except IndexError:
            client = boto3.client('dynamodb', region_name=region)
            engine = Engine(dynamodb=client)

        resp = client.list_tables()
        tables = resp['TableNames']

        models = [Brewoptix,
                  PurchaseOrderNumber,
                  Deployment]

        for model in models:
            model.Meta.table_name = model.Meta.table_name.format(STAGE=stage)

        print('Running dynamodb tables creation script '
              'in Region: {REGION}'.format(REGION=region))
        print("Dynamodb Tables: ")
        for model in models:
            if model.Meta.table_name not in tables:
                print('Creating table: ', model.Meta.table_name)
                engine.bind(model)

        print("Check if autoscaling is enabled")
        try:
            endpoint = args[2]
            autoscaler = AutoScaleDynamodb(dynamo_target_utilization,
                                           scale_in_cooldown,
                                           scale_out_cooldown,
                                           region_name=region,
                                           endpoint_url=endpoint)
        except IndexError:
            autoscaler = AutoScaleDynamodb(dynamo_target_utilization,
                                           scale_in_cooldown,
                                           scale_out_cooldown,
                                           region_name=region)

        print("Autoscaling read units of tables and Global indexes")
        tables = [model.Meta.table_name for model in models]

        status_read_units = autoscaler.get_table_autoscale_status(table_names=tables,
                                                            unit_type='read')

        # We are going to overwrite all tables if they differ from this spec.
        for model in models:
            tb_name = model.Meta.table_name
            can_autoscale = getattr(model.Meta, 'autoscale_table', False)
            if can_autoscale:
                if not status_read_units[tb_name]['enabled'] or \
                        status_read_units[tb_name]['capacity_min'] != model.Meta.read_units_min or \
                        status_read_units[tb_name]['capacity_max'] != model.Meta.read_units_max:
                    print("Autoscaling read units for table {TABLE}".format(TABLE=tb_name))
                    autoscaler.autoscale_table(tb_name,
                                               unit_type='read',
                                               min_capacity=model.Meta.read_units_min,
                                               max_capacity=model.Meta.read_units_max)
                    autoscaler.attach_scaling_policy(tb_name, unit_type='read')

                    if 'autoscale_all_indices' in dir(model.Meta) and model.Meta.autoscale_all_indices:
                        print("Autoscaling read units for all indexes in {TABLE}".format(TABLE=tb_name))
                        for attr in dir(model):
                            if type(getattr(model, attr)) == GlobalSecondaryIndex:
                                index_slug = tb_name + '/index/' + attr
                                autoscaler.autoscale_table(index_slug,
                                                           unit_type='read',
                                                           min_capacity=model.Meta.read_units_min,
                                                           max_capacity=model.Meta.read_units_max,
                                                           resource_type='index')
                                autoscaler.attach_scaling_policy(index_slug,
                                                                 unit_type='read',
                                                                 resource_type='index')

        print("Autoscaling write units of tables and global indexes")
        status_write_units = autoscaler.get_table_autoscale_status(table_names=tables,
                                                             unit_type='write')

        # We are going to overwrite all tables if they differ from this spec.
        for model in models:
            tb_name = model.Meta.table_name
            can_autoscale = getattr(model.Meta, 'autoscale_table', False)
            if can_autoscale:
                if not status_write_units[tb_name]['enabled'] or \
                        status_write_units[tb_name]['capacity_min'] != model.Meta.write_units_min or \
                        status_write_units[tb_name]['capacity_max'] != model.Meta.write_units_max:
                    print("Autoscaling write units for table {TABLE}".format(TABLE=tb_name))
                    autoscaler.autoscale_table(tb_name,
                                               unit_type='write',
                                               min_capacity=model.Meta.write_units_min,
                                               max_capacity=model.Meta.write_units_max)
                    autoscaler.attach_scaling_policy(tb_name, unit_type='write')

                    if 'autoscale_all_indices' in dir(model.Meta) and model.Meta.autoscale_all_indices:
                        print("Autoscaling write units for all indexes in {TABLE}".format(TABLE=tb_name))
                        for attr in dir(model):
                            if type(getattr(model, attr)) == GlobalSecondaryIndex:
                                index_slug = tb_name + '/index/' + attr
                                autoscaler.autoscale_table(index_slug,
                                                           unit_type='write',
                                                           min_capacity=model.Meta.write_units_min,
                                                           max_capacity=model.Meta.write_units_max,
                                                           resource_type='index')
                                autoscaler.attach_scaling_policy(index_slug,
                                                                 unit_type='write',
                                                                 resource_type='index')

        if stage == 'local':
            # RDS Support NotYetImplemented for local development
            sys.exit(0)

        rds_client = boto3.client('rds-data', region_name=region)
        sql_models = [OnHandAurora,
                      ProductionAurora,
                      AdjustmentsAurora,
                      SalesAurora,
                      ProjectionLocksAurora]

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


