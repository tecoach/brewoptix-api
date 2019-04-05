import boto3
from botocore.exceptions import ClientError
from data_common.utils import is_right_datatype
from data_common.exceptions import AuroraSchemaNotFound, AuroraSqlExecuteFailed, \
    AuroraPrimaryKeySignatureMismatch, AuroraConnectionLinkFailure
from uuid import UUID
import time


class AuroraStorage:
    def __init__(self,
                 aurora_db_arn,
                 aurora_db_secret_arn,
                 aurora_db_name,
                 *args, **kwargs):
        self._client = boto3.client(
            'rds-data',
            *args,
            **kwargs
        )
        self._db_arn = aurora_db_arn
        self._db_secret_arn = aurora_db_secret_arn
        self._db_name = aurora_db_name
        # self._RESERVED_NAMES = ["EntityNumber",]

    @property
    def client(self):
        """boto3 client"""
        return self._client

    @client.setter
    def client(self, client):
        """Setter for boto3 client. Used for tests"""
        self._client = client

    def _execute(self, statement, continue_after_timeout=False):
        for i in range(3):
            try:
                response = self._client.execute_statement(
                    secretArn=self._db_secret_arn,
                    database=self._db_name,
                    resourceArn=self._db_arn,
                    sql=statement,
                    continueAfterTimeout=continue_after_timeout)
                return response
            except ClientError as ex:
                print(ex)
                print("Attempt {0}".format(i))
                if ex.response['Error']['Code'] == 'BadRequestException':
                    pass  # Assuming Connection Link error
                else:
                    raise ex

            # LARGE TIMEOUT, pls make sure request handlers using this has enough timeout
            time.sleep(30)
        else:
            raise AuroraConnectionLinkFailure("Tried 3 times and failed")

    def _bulk_execute(self, statement, parameters):
        for i in range(3):
            try:
                response = self._client.batch_execute_statement(
                    secretArn=self._db_secret_arn,
                    database=self._db_name,
                    resourceArn=self._db_arn,
                    sql=statement,
                    parameterSets=parameters)
                return response
            except ClientError as ex:
                print(ex)
                print("Attempt {0}".format(i))
                if ex.response['Error']['Code'] == 'BadRequestException':
                    pass  # Assuming Connection Link error
                else:
                    raise ex

            # LARGE TIMEOUT, pls make sure request handlers using this has enough timeout
            time.sleep(30)
        else:
            raise AuroraConnectionLinkFailure("Tried 3 times and failed")

    def save(self, table, obj):
        # get table schema
        schema_query = """SELECT COLUMN_NAME , DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE 
            TABLE_NAME = '{TABLE_NAME}'""".format(TABLE_NAME=table)

        response = self._execute(schema_query)

        print(response)
        try:
            schema = response["records"]
        except (KeyError, IndexError):
            raise AuroraSchemaNotFound

        schema = [item for item in schema if item[0]['stringValue']]

        # Find primary key
        primary_key_query = """SELECT COLUMN_NAME 
        FROM information_schema.KEY_COLUMN_USAGE 
        WHERE TABLE_NAME = '{TABLE_NAME}' AND CONSTRAINT_NAME = 'PRIMARY'""".format(TABLE_NAME=table)
        response = self._execute(primary_key_query)

        print(response)

        # find value of primary key from obj
        try:
            index = response["records"]
        except (KeyError, IndexError):
            raise AuroraSchemaNotFound

        print(index)
        primary_keys = [item[0]['stringValue'] for item in index]

        # Check if row exists for primary key
        check_statement = "SELECT EXISTS(SELECT * FROM `{TABLE_NAME}` WHERE ".format(TABLE_NAME=table)

        where_items = []
        for row in schema:
            column_name = row[0]
            column_type = row[1]
            key = column_name["stringValue"]
            datatype = column_type["stringValue"]
            if key in primary_keys:
                val = obj.get(key, None)

                if datatype == "binary":
                    if not val:
                        val = ''
                    snippet = '{KEY}=(UNHEX(REPLACE("{VAL}", "-","")))'.format(KEY=key, VAL=val)
                elif datatype == "date" or datatype == "char":
                    snippet = "{KEY}='{VAL}'".format(KEY=key, VAL=val)
                elif datatype == "tinyint":
                    snippet = "{KEY}=".format(KEY=key) + "{VAL}".format(VAL=val).lower()
                else:
                    snippet = '{KEY}={VAL}'.format(KEY=key, VAL=val)
                print(snippet)
                where_items.append(snippet)

        where_clause = " AND ".join(where_items)    # this variable is reused in update entity step below
        check_statement += where_clause
        check_statement += ")"

        response = self._execute(check_statement)

        print(response)

        is_exist = bool(
            response['records'][0][0]['longValue']
        )

        # insert or update obj based on primary key
        if not is_exist:
            # this is an insert save
            # if key not in obj, insert null
            for row in schema:
                key = row[0]["stringValue"]
                if key not in obj:
                    obj[key] = None

            allowed_keys = [row[0]["stringValue"] for row in schema]

            # remove keys not in schema from obj
            obj = {k: v for k, v in obj.items() if k in allowed_keys}

            # convert obj field values to datatype accepted by aurora
            # and build the insert statement
            statement = [
                # "USE {DB_NAME};".format(DB_NAME=self._db_name),
                "INSERT INTO `{TABLE}`".format(TABLE=table),
                "(" + ", ".join(allowed_keys) + ") VALUES ",
            ]

            values = []
            for row in schema:
                column_name = row[0]
                column_type = row[1]
                key = column_name["stringValue"]
                datatype = column_type["stringValue"]

                val = obj[key]

                if datatype == "binary":
                    snippet = '(UNHEX(REPLACE("{VAL}", "-","")))'.format(VAL=val)
                elif datatype == "date" or datatype == "char":
                    snippet = "'{VAL}'".format(VAL=val)
                else:
                    snippet = '{VAL}'.format(VAL=val)

                values.append(snippet)

            statement.append(
                "(" + ", ".join(values) + ")"
            )

            print(statement)
            statement = " ".join(statement)

        else:
            allowed_keys = [row[0]["stringValue"] for row in schema]

            # remove keys not in schema from obj
            obj = {k: v for k, v in obj.items() if k in allowed_keys}

            # convert obj field values to datatype accepted by aurora
            # and build the insert statement
            statement = [
                # "USE {DB_NAME};".format(DB_NAME=self._db_name),
                "UPDATE `{TABLE}`".format(TABLE=table),
                "SET",
            ]

            values = []
            for row in schema:
                column_name = row[0]
                column_type = row[1]
                key = column_name["stringValue"]
                datatype = column_type["stringValue"]

                if key in obj:
                    val = obj[key]

                    if datatype == "binary":
                        snippet = '{KEY} = (UNHEX(REPLACE("{VAL}", "-","")))'.format(KEY=key, VAL=val)
                    elif datatype == "date" or datatype == "char":
                        snippet = "{KEY} = '{VAL}'".format(KEY=key, VAL=val)
                    else:
                        snippet = '{KEY} = {VAL}'.format(KEY=key, VAL=val)

                    values.append(snippet)

            statement.append(
                ", ".join(values)
            )

            statement.append("WHERE " + where_clause)
            statement = " ".join(statement)
            print(statement)

        # execute sql statement
        try:
            response = self._execute(statement, True)
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'StatementTimeoutException':
                pass
            else:
                raise AuroraSqlExecuteFailed(str(ex))

        return obj

    def get_items(self, query):
        try:
            response = self._execute(query)
        except ClientError as ex:
            raise AuroraSqlExecuteFailed(str(ex))

        # type conversion
        records = response["records"]
        results = []
        for record in records:
            result = []
            for item in record:
                dtype = list(item.keys())[0]
                val = list(item.values())[0]

                if dtype == "blobValue":    # uuid
                    result.append(
                        str(UUID(bytes=val))
                    )
                else:
                    result.append(val)
            results.append(result)

        return results

    def delete(self, table, keys_obj):
        """
        keys_obj is a dict with primary key names as dict-keys and
        values we would like to be searched for as dict-vals
        """
        # Find primary key
        primary_key_query = """SELECT COLUMN_NAME 
                        FROM information_schema.KEY_COLUMN_USAGE 
                        WHERE TABLE_NAME = '{TABLE_NAME}' AND CONSTRAINT_NAME = 'PRIMARY'""".format(TABLE_NAME=table)
        response = self._execute(primary_key_query)

        print(response)

        # find value of primary key from obj
        try:
            index = response["records"]
        except (KeyError, IndexError):
            raise AuroraSchemaNotFound

        print(index)
        table_primary_keys = [item[0]['stringValue'] for item in index]

        for k in table_primary_keys:
            if k not in keys_obj:
                raise AuroraPrimaryKeySignatureMismatch("All fields that make the natural key are not present")

        # get table schema
        schema_query = """SELECT COLUMN_NAME , DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE 
                    TABLE_NAME = '{TABLE_NAME}'""".format(TABLE_NAME=table)

        response = self._execute(schema_query)

        print(response)
        try:
            schema = response["records"]
        except (KeyError, IndexError):
            raise AuroraSchemaNotFound

        schema = [item for item in schema if item[0]['stringValue']]

        # Check if row exists for primary key
        delete_statement = "DELETE FROM `{TABLE_NAME}` WHERE ".format(TABLE_NAME=table)

        where_items = []
        for row in schema:
            column_name = row[0]
            column_type = row[1]
            key = column_name["stringValue"]
            datatype = column_type["stringValue"]
            if key in table_primary_keys:
                val = keys_obj.get(key, None)

                if datatype == "binary":
                    if not val:
                        val = ''
                    snippet = '{KEY}=(UNHEX(REPLACE("{VAL}", "-","")))'.format(KEY=key, VAL=val)
                elif datatype == "date" or datatype == "char":
                    snippet = "{KEY}='{VAL}'".format(KEY=key, VAL=val)
                elif datatype == "tinyint":
                    snippet = "{KEY}=".format(KEY=key) + "{VAL}".format(VAL=val).lower()
                else:
                    snippet = '{KEY}={VAL}'.format(KEY=key, VAL=val)
                print(snippet)
                where_items.append(snippet)

        where_clause = " AND ".join(where_items)  # this variable is reused in update entity step below
        delete_statement += where_clause

        response = self._execute(delete_statement)

        print(response)

        return response

    def bulk_insert(self, table, objs):
        # get table schema
        schema_query = """SELECT COLUMN_NAME , DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE 
                    TABLE_NAME = '{TABLE_NAME}'""".format(TABLE_NAME=table)

        response = self._execute(schema_query)

        print(response)
        try:
            schema = response["records"]
        except (KeyError, IndexError):
            raise AuroraSchemaNotFound

        schema = [item for item in schema if item[0]['stringValue']]

        allowed_keys = [row[0]["stringValue"] for row in schema]

        statement = [
            # "USE {DB_NAME};".format(DB_NAME=self._db_name),
            "INSERT INTO `{TABLE}`".format(TABLE=table),
            "(" + ", ".join(allowed_keys) + ") VALUES ",
            "(" + ", ".join(":" + k for k in allowed_keys) + ")"
        ]
        statement = " ".join(statement)

        values_parameters = []
        for obj in objs:
            # this is an insert save
            # if key not in obj, insert null
            for row in schema:
                key = row[0]["stringValue"]
                if key not in obj:
                    obj[key] = None

            # remove keys not in schema from obj
            obj = {k: v for k, v in obj.items() if k in allowed_keys}

            # convert obj field values to datatype accepted by aurora
            # and build the insert statement
            value = []
            for row in schema:
                column_name = row[0]
                column_type = row[1]
                key = column_name["stringValue"]
                datatype = column_type["stringValue"]

                val = obj[key]

                if datatype == "binary":
                    t = 'blobValue'
                    fn = bytes
                elif datatype == "date" or datatype == "char":
                    t = 'stringValue'
                    fn = str
                elif datatype == 'tinyint':
                    t = 'booleanValue'
                    fn = bool
                elif datatype == 'int':
                    t = 'longValue'
                    fn = int
                else:
                    t = 'stringValue'
                    fn = str

                value.append(
                    {
                        'name': key,
                        'value': {
                            t: fn(val)
                        }
                    }
                )

            values_parameters.append(value)

        print("Bulk insert statement")
        print(statement)

        resp = self._bulk_execute(statement, values_parameters)
        print(resp)