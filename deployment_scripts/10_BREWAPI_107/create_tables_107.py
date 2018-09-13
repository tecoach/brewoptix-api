import boto3
from bloop import (
    BaseModel, Boolean, Column, Number, String,
    UUID, Map, List, GlobalSecondaryIndex, Engine
)

class Profile(BaseModel):
    class Meta:
        table_name = 'brewoptix-users'
        read_units = 20
        write_units = 20

    # big 8
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # API attrs
    user_id = Column(UUID)
    affiliate_id = Column(String, default='')
    email = Column(String)

    # this index can be used for checking affiliate_id collision
    by_affiliate_id = GlobalSecondaryIndex(
        projection='keys',
        hash_key='affiliate_id',
        read_units=20,
        write_units=20
    )

    by_user_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='user_id',
        read_units=20,
        write_units=20
    )

    by_email = GlobalSecondaryIndex(
        projection='all',
        hash_key='email',
        read_units=20,
        write_units=20
    )


class Supplier(BaseModel):
    class Meta:
        table_name = 'brewoptix-suppliers'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    name = Column(String)


class Brand(BaseModel):
    class Meta:
        table_name = 'brewoptix-brands'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    name = Column(String)
    supplier_id = Column(UUID)

    by_brand_name = GlobalSecondaryIndex(
        projection='all',
        hash_key='name',
        read_units=20,
        write_units=20
    )

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


class PackageType(BaseModel):
    class Meta:
        table_name = 'brewoptix-package-types'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    supplier_id = Column(UUID)

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


class Product(BaseModel):
    class Meta:
        table_name = 'brewoptix-products'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    supplier_id = Column(UUID)

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


class OnHand(BaseModel):
    class Meta:
        table_name = 'brewoptix-on-hand-inventory'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # API Attrs
    supplier_id = Column(UUID)
    product_id = Column(UUID)

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


class Adjustment(BaseModel):
    class Meta:
        table_name = 'brewoptix-adjustment-inventory'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # API Attrs
    supplier_id = Column(UUID)
    adjustment_date = Column(Number)

    by_supplier_id_and_adjustment_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        range_key='adjustment_date',
        read_units=20,
        write_units=20
    )


class Payments(BaseModel):
    class Meta:
        table_name = 'brewoptix-payments'
        read_units = 20
        write_units = 20

    # big 8
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)
    user_id = Column(UUID)
    timestamp = Column(Number)

    # API attrs
    email = Column(String)

    by_user_id_and_timestamp = GlobalSecondaryIndex(
        projection='all',
        hash_key='user_id',
        range_key='timestamp',
        read_units=20,
        write_units=20
    )

    by_email_and_timestamp = GlobalSecondaryIndex(
        projection='all',
        hash_key='email',
        range_key='timestamp',
        read_units=20,
        write_units=20
    )


class Container(BaseModel):
    class Meta:
        table_name = 'brewoptix-containers'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    supplier_id = Column(UUID)

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


class RetailPackage(BaseModel):
    class Meta:
        table_name = 'brewoptix-retail-packages'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    supplier_id = Column(UUID)

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


class Production(BaseModel):
    class Meta:
        table_name = 'brewoptix-production'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    supplier_id = Column(UUID)
    production_date = Column(Number)    # unix timestamp

    by_supplier_id_and_production_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        range_key='production_date',
        read_units=20,
        write_units=20
    )


class Count(BaseModel):
    class Meta:
        table_name = 'brewoptix-counts'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # API Attrs
    supplier_id = Column(UUID)
    count_date = Column(Number)

    by_supplier_id_and_count_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        range_key='count_date',
        read_units=20,
        write_units=20
    )


class PurchaseOrder(BaseModel):
    class Meta:
        table_name = 'brewoptix-purchase-orders'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # API Attrs
    supplier_id = Column(UUID)
    distributor_id = Column(UUID)
    order_date = Column(Number)
    pack_date = Column(Number)
    ship_date = Column(Number)

    by_supplier_id_and_order_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        range_key='order_date',
        read_units=20,
        write_units=20
    )

    by_supplier_id_and_pack_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        range_key='pack_date',
        read_units=20,
        write_units=20
    )

    by_supplier_id_and_ship_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        range_key='ship_date',
        read_units=20,
        write_units=20
    )

    by_distributor_id_and_order_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='distributor_id',
        range_key='order_date',
        read_units=20,
        write_units=20
    )

    by_distributor_id_and_pack_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='distributor_id',
        range_key='pack_date',
        read_units=20,
        write_units=20
    )

    by_distributor_id_and_ship_date = GlobalSecondaryIndex(
        projection='all',
        hash_key='distributor_id',
        range_key='ship_date',
        read_units=20,
        write_units=20
    )


class PurchaseOrderNumber(BaseModel):
    class Meta:
        table_name = 'brewoptix-purchase-order-number'
        read_units = 20
        write_units = 20

    # Api attrs
    supplier_id = Column(UUID, hash_key=True)


class SupplierDistributor(BaseModel):
    class Meta:
        table_name = 'brewoptix-supplier-distributors'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    supplier_id = Column(UUID)
    name = Column(String)

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


class Distributor(BaseModel):
    class Meta:
        table_name = 'brewoptix-distributors'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)


class Merchandise(BaseModel):
    class Meta:
        table_name = 'brewoptix-merchandise'
        read_units = 20
        write_units = 20

    # big 7
    entity_id = Column(UUID, hash_key=True)
    version = Column(UUID, range_key=True)

    # Api attrs
    supplier_id = Column(UUID)
    name = Column(String)

    by_supplier_id = GlobalSecondaryIndex(
        projection='all',
        hash_key='supplier_id',
        read_units=20,
        write_units=20
    )


if __name__ == '__main__':
    import sys

    args = sys.argv
    if len(args) >= 3:
        region = args[1]
        stage = args[2]

        client = boto3.client('dynamodb', region_name=region)
        engine = Engine(dynamodb=client)

        resp = client.list_tables()
        tables = resp['TableNames']

        models = [Profile,
                  Supplier,
                  Brand,
                  PackageType,
                  Product,
                  OnHand,
                  Adjustment,
                  Payments,
                  Container,
                  RetailPackage,
                  Production,
                  Count,
                  PurchaseOrder,
                  PurchaseOrderNumber,
                  Merchandise,
                  SupplierDistributor,
                  Distributor]

        print('Running dynamodb tables creation script '
              'in Region: {REGION}'.format(REGION=region))
        print("Dynamodb Tables: ")
        for model in models:
            if model.Meta.table_name not in tables:
                print('Creating table: ', model.Meta.table_name)
                engine.bind(model)

    else:
        print("""FAILED: Running dynamodb tables creation script.
                 REGION needs to be passed as a positional argument
                 while running the script""")


