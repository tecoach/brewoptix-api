from data_adapter import DynamoStorage
from auth0_adapter import Auth0
from aurora_adapter import AuroraStorage

from data_common.repository import Repository
from repository.profile \
    import DynamoProfileRepository
from repository.suppliers \
    import DynamoSuppliersRepository
from repository.brands \
    import DynamoBrandsRepository
from repository.package_types \
    import DynamoPackageTypeRepository
from repository.products \
    import DynamoProductRepository
from repository.on_hand \
    import DynamoOnHandRepository
from repository.adjustment \
    import DynamoAdjustmentRepository
from repository.payments \
    import DynamoPaymentsRepository
from repository.containers \
    import DynamoContainerRepository
from repository.retail_packages \
    import DynamoRetailPackageRepository
from repository.production \
    import DynamoProductionRepository
from repository.counts \
    import DynamoCountRepository
from repository.purchase_orders \
    import DynamoPurchaseOrderRepository
from repository.inventory \
    import AuroraInventoryRepository
from repository.supplier_distributors \
    import DynamoSupplierDistributorsRepository
from repository.distributor_suppliers \
    import DynamoDistributorSuppliersRepository
from repository.merchandise \
    import DynamoMerchandiseRepository
from repository.distributors \
    import DynamoDistributorsRepository


class DynamoRepository(Repository,
                       DynamoProfileRepository,
                       DynamoSuppliersRepository,
                       DynamoBrandsRepository,
                       DynamoPackageTypeRepository,
                       DynamoProductRepository,
                       DynamoOnHandRepository,
                       DynamoAdjustmentRepository,
                       DynamoPaymentsRepository,
                       DynamoContainerRepository,
                       DynamoRetailPackageRepository,
                       DynamoProductionRepository,
                       DynamoCountRepository,
                       DynamoPurchaseOrderRepository,
                       AuroraInventoryRepository,
                       DynamoSupplierDistributorsRepository,
                       DynamoDistributorSuppliersRepository,
                       DynamoMerchandiseRepository,
                       DynamoDistributorsRepository
                       ):
    def __init__(self,
                 region_name,
                 table,
                 user_id=None,
                 email='',
                 aurora_db_arn='',
                 aurora_db_secret_arn='',
                 aurora_db_name='',
                 dynamodb_local_endpoint=None):
        # dynamodb_local_endpoint if present is used to patch the dynamodb boto client to
        # use a local db instance instead of going to AWS

        super(Repository, self).__init__(region_name, user_id, email)

        if dynamodb_local_endpoint:
            self._storage = DynamoStorage(table=table, user_id=user_id, endpoint_url=dynamodb_local_endpoint)
        else:
            self._storage = DynamoStorage(table=table, user_id=user_id, )

        self._auth0 = Auth0(user_id)

        self._aurora_storage = AuroraStorage(aurora_db_arn, aurora_db_secret_arn, aurora_db_name)
