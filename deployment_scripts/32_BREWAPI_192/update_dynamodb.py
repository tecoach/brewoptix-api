import os
import sys
import json
import boto3
from bloop import (
    BaseModel, Boolean, Column, Number, String,
    UUID, Map, List, GlobalSecondaryIndex, Engine
)
from autoscaling_utils import AutoScaleDynamodb


class DistributorSupplier(BaseModel):
    class Meta:
        table_name = 'brewoptix-distributor-suppliers'
        read_units_min = 2
        read_units_max = 20
        write_units_min = 2
        write_units_max = 20
        autoscale_table = True
        autoscale_all_indices = True

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    distributor_id = Column(UUID)
    supplier_distributor_id = Column(UUID)
    supplier_id = Column(UUID)
    nickname = Column(String)
    access_code = Column(String, default='')

    by_distributor_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='distributor_id',
    )

    by_access_code = GlobalSecondaryIndex(
        projection='all',
        hash_key='access_code',
    )


if __name__ == '__main__':

    args = sys.argv
    if len(args) >= 2:
        stage = args[1]

        os.environ['STAGE'] = stage

        config_filename = 'config.' + stage + '.json'
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
            resource = boto3.resource('dynamodb', region_name=region, endpoint_url=endpoint)
        except IndexError:
            client = boto3.client('dynamodb', region_name=region)
            resource = boto3.resource('dynamodb', region_name=region)

        response = client.describe_table(TableName='brewoptix-distributor-suppliers')
        global_indexes = response['Table']['GlobalSecondaryIndexes']
        index_list = [index['IndexName'] for index in global_indexes]
        if 'by_access_code' not in index_list:
            print('Updating brewoptix-distributor-suppliers table')

            table = resource.Table('brewoptix-distributor-suppliers')

            print('Adding Global Secondary index by_access_code on brewoptix-supplier-distributors')
            response = client.update_table(
                TableName=DistributorSupplier.Meta.table_name,
                AttributeDefinitions=[
                    {'AttributeName': 'access_code', 'AttributeType': 'S'}],
                GlobalSecondaryIndexUpdates=[
                    {
                        'Create': {
                            'IndexName': 'by_access_code',
                            'KeySchema': [
                                {
                                    'AttributeName': 'access_code',
                                    'KeyType': 'HASH'
                                }
                            ],
                            'Projection': {
                                'ProjectionType': 'ALL'
                            },
                            'ProvisionedThroughput': {
                                'ReadCapacityUnits': 4,
                                'WriteCapacityUnits': 4
                            }
                        }
                    }
                ],
            )

        models = [DistributorSupplier, ]
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