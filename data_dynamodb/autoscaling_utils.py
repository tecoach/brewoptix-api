import boto3


class AutoScaleDynamodb():
    def __init__(self,
                 dynamo_target_utilization=70.0,
                 scale_in_cooldown=60,
                 scale_out_cooldown=60,
                 *args, **kwargs):
        self._client = boto3.client(
            'application-autoscaling',
            *args,
            **kwargs
        )
        self.target_utilization = dynamo_target_utilization
        self.scale_in_cooldown = scale_in_cooldown
        self.scale_out_cooldown = scale_out_cooldown

    def autoscale_table(self, resource_name,
                        unit_type='read',
                        min_capacity=2,
                        max_capacity=20,
                        resource_type='table'
                        ):
        if resource_type not in ['table', 'index']:
            raise Exception('Resource type must be one of "table, index"')

        if unit_type == 'read':
            self._client.register_scalable_target(ServiceNamespace='dynamodb',
                                                  ResourceId='table/{RESOURCE}'.format(RESOURCE=resource_name),
                                                  ScalableDimension='dynamodb:{RESOURCE_TYPE}:ReadCapacityUnits'.format(RESOURCE_TYPE=resource_type),
                                                  MinCapacity=min_capacity,
                                                  MaxCapacity=max_capacity)
        elif unit_type == 'write':
            self._client.register_scalable_target(ServiceNamespace='dynamodb',
                                                  ResourceId='table/{RESOURCE}'.format(RESOURCE=resource_name),
                                                  ScalableDimension='dynamodb:{RESOURCE_TYPE}:WriteCapacityUnits'.format(RESOURCE_TYPE=resource_type),
                                                  MinCapacity=min_capacity,
                                                  MaxCapacity=max_capacity)
        else:
            raise TypeError('unknown unit type')

    def attach_scaling_policy(self, resource_name,
                              unit_type='read',
                              resource_type='table'
                              ):
        """
        Target Tracking Scaling policy
        """
        if unit_type == 'read':
            self._client.put_scaling_policy(ServiceNamespace='dynamodb',
                                            ResourceId='table/{TABLE}'.format(TABLE=resource_name),
                                            PolicyType='TargetTrackingScaling',
                                            PolicyName='ScaleDynamoDBReadCapacityUtilization',
                                            ScalableDimension='dynamodb:{RESOURCE_TYPE}:ReadCapacityUnits'.format(RESOURCE_TYPE=resource_type),
                                            TargetTrackingScalingPolicyConfiguration={
                                                'TargetValue': self.target_utilization,
                                                'PredefinedMetricSpecification': {
                                                    'PredefinedMetricType': 'DynamoDBReadCapacityUtilization'
                                                },
                                                'ScaleOutCooldown': self.scale_out_cooldown,
                                                'ScaleInCooldown': self.scale_in_cooldown
                                            })
        elif unit_type == 'write':
            self._client.put_scaling_policy(ServiceNamespace='dynamodb',
                                            ResourceId='table/{TABLE}'.format(TABLE=resource_name),
                                            PolicyType='TargetTrackingScaling',
                                            PolicyName='ScaleDynamoDBWriteCapacityUtilization',
                                            ScalableDimension='dynamodb:{RESOURCE_TYPE}:WriteCapacityUnits'.format(RESOURCE_TYPE=resource_type),
                                            TargetTrackingScalingPolicyConfiguration={
                                                'TargetValue': self.target_utilization,
                                                'PredefinedMetricSpecification': {
                                                    'PredefinedMetricType': 'DynamoDBWriteCapacityUtilization'
                                                },
                                                'ScaleOutCooldown': self.scale_out_cooldown,
                                                'ScaleInCooldown': self.scale_in_cooldown
                                            })
        else:
            raise TypeError('unknown unit type')

    def get_table_autoscale_status(self, table_names, unit_type='read'):
        """
        Checks if autoscaling is enabled in a table
        """
        table_ids = ['table/{RESOURCE}'.format(RESOURCE=resource_name) for resource_name in table_names]
        resource_statuses = {resource_name: {'enabled': False} for resource_name in table_names}

        if unit_type == 'read':
            resp = self._client.describe_scalable_targets(
                ServiceNamespace='dynamodb',
                ResourceIds=table_ids,
                ScalableDimension='dynamodb:table:ReadCapacityUnits',
                MaxResults=200,
            )
        elif unit_type == 'write':
            resp = self._client.describe_scalable_targets(
                ServiceNamespace='dynamodb',
                ResourceIds=table_ids,
                ScalableDimension='dynamodb:table:WriteCapacityUnits',
                MaxResults=200,
            )
        else:
            raise TypeError('Unknown unit type')

        results = resp['ScalableTargets']

        for result in results:
            resource_name = result['ResourceId'].split('table/')[1]
            resource_statuses[resource_name]['enabled'] = True
            resource_statuses[resource_name]['capacity_min'] = result['MinCapacity']
            resource_statuses[resource_name]['capacity_max'] = result['MaxCapacity']

        return resource_statuses
