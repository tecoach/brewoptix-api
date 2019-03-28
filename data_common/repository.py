import abc
import os


class BaseRepository:
    def __init__(self, region_name, user_id=None, email=''):
        self._region_name = region_name
        self._user_id = user_id
        self._email = email
        self._stage = os.environ["STAGE"]
    # If more attributes are required, modify SQSManager, SnsNotifier class as well to match with this signature


class ProfileRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_or_create_profile(self):
        pass

    @abc.abstractmethod
    def update_profile(self, obj):
        pass

    @abc.abstractmethod
    def update_user_app_metadata(self, obj):
        pass

    @abc.abstractmethod
    def delete_profile(self):
        pass


class SupplierRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_supplier(self, obj):
        pass

    @abc.abstractmethod
    def get_supplier_by_id(self, entity_id):
        pass

    @abc.abstractmethod
    def delete_supplier_by_id(self, entity_id):
        pass

    @abc.abstractmethod
    def get_all_suppliers(self, suppliers):
        pass

    @abc.abstractmethod
    def upsert_user_in_supplier(self, supplier_id, obj):
        pass

    @abc.abstractmethod
    def delete_user_in_supplier(self, supplier_id, retiring_user_id):
        pass

    @abc.abstractmethod
    def get_all_users_in_supplier(self, supplier_id):
        pass


class BrandRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_brand(self, obj):
        pass

    @abc.abstractmethod
    def get_brand_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_brand_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_brands(self, supplier):
        pass


class PackageTypeRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_package_type(self, obj):
        pass

    @abc.abstractmethod
    def get_package_type_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_package_type_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_package_types(self, supplier_id):
        pass


class ProductRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_product(self, obj):
        pass

    @abc.abstractmethod
    def get_product_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_product_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_products(self, supplier_id):
        pass


class OnHandRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_on_hand(self, obj):
        pass

    @abc.abstractmethod
    def get_on_hand_record_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_on_hand_record_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_on_hands(self, supplier_id):
        pass

    @abc.abstractmethod
    def process_projections_queue(self, supplier_id, brand_id, package_type_id, start_date, request_id):
        pass

    # Methods like ones below can be added in future
    # def get_on_hand_by_supplier_id_and_observation_date()


class AdjustmentRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_adjustment(self, obj):
        pass

    @abc.abstractmethod
    def get_adjustment_record_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_adjustment_record_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_adjustments(self, supplier_id):
        pass

    @abc.abstractmethod
    def get_adjustment_by_adjustment_date_range(self, supplier_id, min_adjustment_date, max_adjustment_date):
        pass

    @abc.abstractmethod
    def process_adjustments_queue(self, obj):
        pass


class PaymentsRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def charge_by_stripe(self, obj):
        pass

    @abc.abstractmethod
    def get_all_payments(self):
        pass


class ContainerRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_container(self, obj):
        pass

    @abc.abstractmethod
    def get_container_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_container_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_containers(self, supplier_id):
        pass


class RetailPackageRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_retail_package(self, obj):
        pass

    @abc.abstractmethod
    def get_retail_package_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_retail_package_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_retail_packages(self, supplier_id):
        pass


class ProductionRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_production(self, obj):
        pass

    @abc.abstractmethod
    def get_production_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_production_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_production(self, supplier_id):
        pass

    @abc.abstractmethod
    def get_production_by_production_date_range(self, supplier_id, min_production_date, max_production_date):
        pass

    @abc.abstractmethod
    def process_production_queue(self, obj):
        pass


class CountRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_count(self, obj):
        pass

    @abc.abstractmethod
    def get_count_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_count_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_counts(self, supplier_id):
        pass

    @abc.abstractmethod
    def get_count_by_count_date_range(self, supplier_id, min_count_date, max_count_date):
        pass

    @abc.abstractmethod
    def process_counts_queue(self, obj):
        pass


class PurchaseOrderRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_purchase_order(self, obj):
        pass

    @abc.abstractmethod
    def get_purchase_order_by_id(self, entity_id, supplier_id, distributors):
        pass

    @abc.abstractmethod
    def delete_purchase_order_by_id(self, entity_id, supplier_id, distributors):
        pass

    @abc.abstractmethod
    def get_purchase_orders_by_order_date_range(self, min_order_date, max_order_date,
                                                supplier_id, distributors):
        pass

    @abc.abstractmethod
    def get_purchase_orders_by_pack_date_range(self, min_pack_date, max_pack_date,
                                               supplier_id, distributors):
        pass

    @abc.abstractmethod
    def get_purchase_orders_by_ship_date_range(self, min_ship_date, max_ship_date,
                                               supplier_id, distributors):
        pass

    @abc.abstractmethod
    def get_purchase_order_by_version(self, entity_id, version):
        pass

    @abc.abstractmethod
    def process_purchase_orders_queue(self, obj):
        pass


class InventoryRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_inventory_products_by_date_range(self, supplier_id, start_date, end_date):
        pass


class SupplierDistributorsRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_supplier_distributor(self, obj):
        pass

    @abc.abstractmethod
    def get_supplier_distributor_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_supplier_distributor_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_supplier_distributors(self, supplier_id):
        pass

    @abc.abstractmethod
    def get_supplier_distributor_by_access_code(self, access_code):
        pass


class DistributorSuppliersRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_distributor_supplier(self, obj):
        pass

    @abc.abstractmethod
    def get_distributor_supplier_by_id(self, distributor_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_distributor_supplier_by_id(self, distributor_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_distributor_supplier_by_access_code(self, supplier_id, access_code):
        pass

    @abc.abstractmethod
    def get_all_distributor_suppliers(self, distributor_id):
        pass


class DistributorsRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_all_distributors(self, distributors):
        pass

    @abc.abstractmethod
    def save_distributor(self, obj):
        pass

    @abc.abstractmethod
    def get_distributor_by_id(self, entity_id):
        pass

    @abc.abstractmethod
    def delete_distributor_by_id(self, entity_id):
        pass

    @abc.abstractmethod
    def upsert_user_in_distributor(self, distributor_id, obj):
        pass

    @abc.abstractmethod
    def delete_user_in_distributor(self, distributor_id, retiring_user_id):
        pass

    @abc.abstractmethod
    def get_all_users_in_distributor(self, distributor_id):
        pass


class MerchandiseRepository(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save_merchandise(self, obj):
        pass

    @abc.abstractmethod
    def get_merchandise_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def delete_merchandise_by_id(self, supplier_id, entity_id):
        pass

    @abc.abstractmethod
    def get_all_merchandises(self, supplier):
        pass


class Repository(ProfileRepository,
                 SupplierRepository,
                 BrandRepository,
                 PackageTypeRepository,
                 ProductRepository,
                 OnHandRepository,
                 AdjustmentRepository,
                 PaymentsRepository,
                 ContainerRepository,
                 RetailPackageRepository,
                 ProductionRepository,
                 CountRepository,
                 PurchaseOrderRepository,
                 InventoryRepository,
                 SupplierDistributorsRepository,
                 DistributorsRepository,
                 BaseRepository,
                 metaclass=abc.ABCMeta):
    pass
