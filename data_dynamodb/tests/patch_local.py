# taken from
# https://bloop.readthedocs.io/en/latest/user/patterns.html and
# https://github.com/numberoverzero/bloop/issues/124
class PatchedDynamoDBClient:
    def __init__(self, real_client):
        self.__client = real_client
        self.mock_ttl = {}
        self.mock_backups = {}

    def describe_time_to_live(self, TableName, **_):
        r = "ENABLED" if self.mock_ttl.get(TableName) else "DISABLED"
        return {"TimeToLiveDescription": {"TimeToLiveStatus": r}}

    def describe_continuous_backups(self, TableName, **_):
        r = "ENABLED" if self.mock_backups.get(TableName) else "DISABLED"
        return {"ContinuousBackupsDescription": {"ContinuousBackupsStatus": r}}

    # TODO override any other methods that DynamoDBLocal doesn't provide

    def __getattr__(self, name):
        # use the original client for everything else
        return getattr(self.__client, name)


def patch_engine(engine):
    client = PatchedDynamoDBClient(engine.session.dynamodb_client)
    engine.session.dynamodb_client = client
    return client
