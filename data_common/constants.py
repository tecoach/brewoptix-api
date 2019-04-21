# Global Constants

# Metadata associated with all data stored
# Also called Big-7
base_attributes = ["entity_id", "version", "previous_version", "active", "latest", "changed_by_id", "changed_on"]

# Attributes used only for tracking and internal use
private_base_attributes = ["previous_version", "active", "latest"]

# API data structures

supplier_attributes = {
    "name": str,
    "main_contact_id": str,
}

brand_attributes = {
    "name": str,
    "supplier_id": "uuid",
    "core_or_seasonal": str,
    "is_active": bool,
    "has_logo": bool,
}

package_type_attributes = {
    "name": str,
    "quantity": int,
    "ordinal": int,
    "retail_package_id": "uuid",
    "supplier_id": "uuid",
}

product_attributes = {
    "supplier_id": "uuid",
    "brand_id": "uuid",
    "package_type_id": "uuid",
}

on_hand_attributes = {
    "package_type_id": "uuid",
    "supplier_id": "uuid",
    "brand_id": "uuid",
    "quantity": int,
    "observation_date": "date",
    "actual": bool,
}

adjustment_attributes = {
    "product_id": "uuid",
    "supplier_id": "uuid",
    "brand_id": "uuid",
    "package_type_id": "uuid",
    "quantity": int,
    "adjustment_date": "date",
    "adjustment_type": str,
}

container_attributes = {
    "name": str,
    "volume": float,
    "volume_uom": str,
    "type": str,
    "global": bool,
    "supplier_id": "uuid",
}

retail_package_attributes = {
    "name": str,
    "quantity": int,
    "container_id": "uuid",
    "supplier_id": "uuid",
}

production_attributes = {
    "supplier_id": "uuid",
    "production_date": "date",
    "products": list,
}

count_attributes = {
    "supplier_id": "uuid",
    "count_date": "date",
    "products": list,
    "package_types": list,
    "status": str,
}

purchase_order_attributes = {
    "supplier_id": "uuid",
    "distributor_name": str,
    "order_date": "date",
    "products": list,
}

supplier_distributors_attributes = {
    "supplier_id": "uuid",
    "name": str,
    "allow_ordering": bool,
    "access_code": str,
}

distributor_suppliers_attributes = {
    "distributor_id": "uuid",
    "supplier_distributor_id": "uuid",
    "supplier_id": "uuid",
    "nickname": str,
    "access_code": str,
}

distributors_attributes = {
    "name": str,
}

merchandise_attributes = {
    "supplier_id": "uuid",
    "name": str,
}
