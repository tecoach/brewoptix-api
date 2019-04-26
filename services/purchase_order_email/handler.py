import os
import sys
import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from log_config import logger

sys.path.append('../../data_dynamodb')
sys.path.append('../../data_common')
sys.path.append('data_dynamodb')
sys.path.append('data_common')
from data_dynamodb.dynamodb_repository import DynamoRepository

Q_NAME_EMAIL_TRANSMITTER = os.getenv('Q_NAME_EMAIL_TRANSMITTER')
PO_EMAIL_TEMPLATE_NAME = os.getenv('PO_EMAIL_TEMPLATE_NAME')


def get_formatted_date(unformatted_date):
    t = datetime.utcfromtimestamp(int(unformatted_date))
    return t.strftime("%m-%d-%Y")


def get_formatted_date_from_string(date_string):
    date_parts = date_string.split("-")
    return date_parts[1] + "-" + date_parts[2] + "-" + date_parts[0]

def create_base_message_data(order_data):
    message_data = {}
    if "distributor_name" in order_data:
        message_data['distributor_name'] = order_data['distributor_name']

    if "supplier_id" in order_data:
        message_data['supplier_id'] = order_data['supplier_id']

    if "order_date" in order_data:
        message_data['order_date'] = get_formatted_date(order_data['order_date'])

    if "pack_date" in order_data:
        message_data['pack_date'] = get_formatted_date(order_data['pack_date'])

    if "ship_date" in order_data:
        message_data['ship_date'] = get_formatted_date(order_data['ship_date'])

    if "order_number" in order_data:
        message_data['order_number'] = order_data['order_number']

    if "po_number" not in order_data or order_data['po_number'] is None:
        message_data['po_number'] = ""
    else:
        message_data['po_number'] = order_data['po_number']

    message_data["action"] = "Created"
    message_data["product_table"] = ""
    message_data["merchandise_table"] = ""
    if "weight" in order_data and "weight_uom" in order_data and order_data["weight_uom"] is not None:
        message_data["weight"] = f'{order_data["weight"]:,}' + " " + order_data["weight_uom"]
    else:
        message_data["weight"] = "N/A"

    if "number_of_pallets" in order_data:
        pallets = order_data["number_of_pallets"]
        if pallets and int(pallets) > 0:
            message_data["pallets"] = pallets
        else:
            message_data["pallets"] = "N/A"
    else:
        message_data["pallets"] = "N/A"

    if "notes" in order_data:
        message_data["notes"] = order_data["notes"]

    if "notes" not in message_data or message_data["notes"] is None:
        message_data["notes"] = ""

    message_data["supplier_name"] = ""

    return message_data


def get_products(order):
    if "products" in order:
        return order["products"]

    return {}


def get_merchandise(order):
    if "merchandise" in order:
        return order["merchandise"]

    return {}


def get_ordered_list_of_brands(products):
    brands = {}

    for brand in products:
        brands[brand["brand_id"]] = brand["brand_name"]

    sorted_brands = sorted(brands.items(), key=lambda kv: kv[1])

    return sorted_brands


def get_lookup(products):
    lookup = {"brands": {}, "products": {}}
    for brand in products:
        brand_id = brand["brand_id"]
        brand_name = brand["brand_name"]
        lookup["brands"][brand_id] = brand_name
        for brand_product in brand["brandProducts"]:
            lookup["products"][brand_product["product_id"]] = brand_product["quantity"]

    return lookup


def get_repo(user_id):
    if "DYNAMO_ENDPOINT" in os.environ:
        return DynamoRepository(
            region_name=os.environ['REGION'],
            table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
            user_id=user_id,
            dynamodb_local_endpoint=os.environ['DYNAMO_ENDPOINT']
        )

    return DynamoRepository(
        region_name=os.environ['REGION'],
        table='brewoptix-{STAGE}'.format(STAGE=os.environ['STAGE']),
        user_id=user_id
    )


def get_previous_order(entity_id, version_id, user_id):
    repo = get_repo(user_id)

    prev_obj = repo.get_purchase_order_by_version(entity_id, version_id)

    return prev_obj


def get_brand_row(brand_name, added, deleted):
    row_text = "<tr><td colspan=2"
    if added:
        row_text += " style='background: #ffff66'><b>" + brand_name + "</b></td>"
    if deleted:
        row_text += "><del>" + brand_name + "</del></td>"

    if not added and not deleted:
        row_text = "<tr><td colspan=2><b>" + brand_name + "</b></td>"

    row_text += "</tr>"

    return row_text


def get_brand_products(products, brand_id):
    for product in products:
        if product["brand_id"] == brand_id:
            return product["brandProducts"]


def get_product_row(quantity, package, product_status):
    row_text = ""

    if product_status == "quantity_changed":
        row_text += "<tr><td> &nbsp; &nbsp; </td><td><span style='background: #ffff66'>" + quantity + \
                    "</span> &nbsp;  " + package + "</td></tr>"
    if product_status == "added" and int(quantity) > 0:
        row_text += "<tr><td> &nbsp; &nbsp; </td><td style='background: #ffff66'>" + quantity + \
                    " &nbsp;  " + package + "</td></tr>"
    if product_status == "normal" and int(quantity) > 0:
        row_text += "<tr><td width=10% nowrap> &nbsp; &nbsp; </td><td>" + quantity + " &nbsp;  " + package + "</td></tr>"

    if product_status == "deleted":
        row_text += "<tr><td> &nbsp; &nbsp; </td><td><del>" + quantity + " &nbsp;  " + package + "</del></td></tr>"

    return row_text


def is_brand_added(brand_id, previous_lookup):
    if brand_id in previous_lookup["brands"]:
        return False

    return True


def get_product_status(product, previous_lookup):
    product_id = product["product_id"]
    quantity = product["quantity"]

    if quantity is None:
        quantity = 0

    if product_id not in previous_lookup["products"]:
        return "added"

    previous_quantity = previous_lookup["products"][product_id]

    if previous_quantity is None:
        previous_quantity = 0

    if previous_quantity == 0 and quantity > 0:
        return "added"

    if previous_quantity > 0 and quantity == 0:
        return "deleted"

    if previous_quantity != quantity:
        return "quantity_changed"

    return "normal"


def create_product_table(order_data, previous_order_data):
    current_products = get_products(order_data)
    current_lookup = get_lookup(current_products)

    is_new = previous_order_data == {}

    previous_products = get_products(previous_order_data)
    previous_lookup = get_lookup(previous_products)

    table_text = ""
    if not order_data["active"]:
        table_text = "<p style='font-weight:bold;color:red;font-size:14px'>THIS ORDER HAS BEEN CANCELLED.  " \
                     "THE ITEMS BELOW ARE NO LONGER GOING TO BE SHIPPED. </p>"

    table_text = table_text + "<table width=100%>"

    brand_list = get_ordered_list_of_brands(current_products)

    for brand in brand_list:
        brand_id = brand[0]
        brand_name = brand[1]
        added = False
        deleted = False
        if not is_new:
            added = is_brand_added(brand_id, previous_lookup)

        table_text += get_brand_row(brand_name, added, deleted)

        brand_products = get_brand_products(current_products, brand_id)
        for product in brand_products:
            product_status = "normal"
            quantity = product["quantity"]
            if quantity is None:
                quantity = 0
            quantity = str(quantity)
            package = product["package_type_name"]
            if not is_new:
                product_status = get_product_status(product, previous_lookup)
                # We want to display the previous quantity instead of "0" when a product is deleted.
                if product_status == "deleted":
                    product_id = product["product_id"]
                    previous_quantity = previous_lookup["products"][product_id]
                    if previous_quantity is None:
                        previous_quantity = 0
                    quantity = str(previous_quantity)

            table_text += get_product_row(quantity, package, product_status)

    previous_brand_list = get_ordered_list_of_brands(previous_products)
    for brand in previous_brand_list:
        brand_id = brand[0]
        brand_name = brand[1]
        deleted = brand_id not in current_lookup["brands"]
        added = False
        if deleted:
            table_text += get_brand_row(brand_name, added, deleted)

            brand_products = get_brand_products(previous_products, brand_id)
            for product in brand_products:
                quantity = product["quantity"]
                if quantity is None:
                    quantity = 0
                quantity = str(quantity)
                package = product["package_type_name"]
                product_status = "deleted"
                if int(product["quantity"]) > 0:
                    table_text += get_product_row(quantity, package, product_status)

    table_text += "</table>"

    return table_text


def get_merchandise_status(merchandise, previous_merchandise):
    merchandise_id = merchandise["merchandise_id"]
    for item in previous_merchandise:
        if item["merchandise_id"] == merchandise_id:
            return "normal"

    return "added"


def get_size_quantity_status(size_quantity, previous_merchandise_version):
    if "merchandise_size_quantities" not in previous_merchandise_version:
        return "normal"

    for previous_size_quantity in previous_merchandise_version["merchandise_size_quantities"]:
        if previous_size_quantity["size"] == size_quantity["size"] and \
                previous_size_quantity["quantity"] != size_quantity["quantity"]:
            return "changed"

    return "normal"


def get_merchandise_row(merchandise, status, previous_merchandise = {}):
    merchandise_name = merchandise["merchandise_name"]
    merchandise_id = merchandise["merchandise_id"]
    row_text = "<tr><td colspan=2 "
    if status == "added":
        row_text += " style='background: #ffff66'"

    row_text += ">"
    if status == "deleted":
        row_text += "<del>"

    row_text += merchandise_name

    if status == "deleted":
        row_text += "</del>"

    row_text += "</td></tr>"
    if "merchandise_size_quantities" in merchandise:
        row_text += "<tr><td width=10% nowrap> &nbsp; &nbsp; </td>"
        previous_merchandise_version = {}
        for item in previous_merchandise:
            if item["merchandise_id"] == merchandise_id:
                previous_merchandise_version = item
                break

        for size_quantity in merchandise["merchandise_size_quantities"]:
            size_status = get_size_quantity_status(size_quantity, previous_merchandise_version)
            row_text += "<td width=10% nowrap"
            if status == "added":
                row_text += " style='background: #ffff66'"
            row_text += ">"

            if status == "deleted":
                row_text += "<del>"

            if size_status == "changed" and status == "normal":
                row_text += "<span style='background: #ffff66'>" + str(size_quantity["quantity"]) + "</span> &nbsp; "
            else:
                row_text += str(size_quantity["quantity"]) + " &nbsp; "

            if size_quantity["size"] != "Quantity":
                 row_text += size_quantity["size"]
            else:
                row_text += " Each"

            if status == "deleted":
                row_text += "</del>"

            row_text += "</td>"

    row_text += "</tr>"

    return row_text


def create_merchandise_table(order_data, previous_order_data):
    current_merchandise = get_merchandise(order_data)

    previous_merchandise = get_merchandise(previous_order_data)
    is_new = previous_order_data == {}

    if len(current_merchandise) == 0 and len(previous_merchandise) == 0:
        return ""

    table_text = "<table width=100%><tr><td colspan=2><b>Merchandise</b></td></tr>"

    for merchandise in current_merchandise:
        merchandise_status = "normal"
        if not is_new:
            merchandise_status = get_merchandise_status(merchandise, previous_merchandise)
        table_text += get_merchandise_row(merchandise, merchandise_status, previous_merchandise)

    for merchandise in previous_merchandise:
        merchandise_status = get_merchandise_status(merchandise, current_merchandise)
        if merchandise_status == "added":
            table_text += get_merchandise_row(merchandise, "deleted")

    table_text += "</table>"

    return table_text


def check_for_updated_data(order_data, previous_order_data, message_data, property_name):
    if property_name in order_data and property_name in previous_order_data:
        old_value = previous_order_data[property_name]
        new_value = order_data[property_name]

        if property_name == "ship_date":
            old_value = get_formatted_date_from_string(old_value)
            new_value = get_formatted_date(new_value)

        if new_value != old_value:
            message_data[property_name] = "<span style='background: #ffff66'>" + message_data[property_name] + "</span>"


def create_full_message_data(order_data, previous_order_data, supplier, created_by_user):
    message_data = create_base_message_data(order_data)
    if previous_order_data != {}:
        if order_data["active"]:
            message_data["action"] = "Updated"
            check_for_updated_data(order_data, previous_order_data, message_data, "ship_date")
            check_for_updated_data(order_data, previous_order_data, message_data, "notes")

            order_data["pallets"] = order_data["number_of_pallets"]
            previous_order_data["pallets"] = previous_order_data["number_of_pallets"]
            check_for_updated_data(order_data, previous_order_data, message_data, "pallets")
        else:
            message_data["action"] = "Cancelled"

    message_data["product_table"] = create_product_table(order_data, previous_order_data)
    message_data["merchandise_table"] = create_merchandise_table(order_data, previous_order_data)
    message_data["supplier_name"] = supplier["name"]

    if "name" in created_by_user:
        message_data["created_by_name"] = created_by_user["name"]
    elif "firstname" in created_by_user and "lastname" in created_by_user:
        message_data["created_by_name"] = created_by_user["firstname"] + " " + created_by_user["lastname"]
    elif "nickname" in created_by_user:
        message_data["created_by_name"] = created_by_user["nickname"]
    else:
        message_data["created_by_name"] = created_by_user["entity_id"]

    return message_data


def get_main_contact(company):
    if company is None:
        return None

    for user in company['users']:
        if company['main_contact_id'] == user['user_id']:
            if "email" in user:
                return user['email']
            if "user_name" in user:
                return user['user_name']

    return None


def get_to_email_list(supplier, distributor, order_placed_user):
    if "email" in order_placed_user:
        order_placed_user_email = order_placed_user['email']
        to_email_list = [order_placed_user_email]
    else:
        to_email_list=[]

    main_supplier_email = get_main_contact(supplier)
    if main_supplier_email and "@" in main_supplier_email:
        to_email_list.append(main_supplier_email)

    main_distributor_email = get_main_contact(distributor)
    if main_distributor_email and "@" in main_distributor_email:
        to_email_list.append(main_distributor_email)

    if "po_email_list" in supplier:
        for email_id in supplier["po_email_list"]:
            if "@" in email_id:
                to_email_list.append(email_id)

    to_email_list = list(set(to_email_list))

    return to_email_list


def get_supplier(order):
    user_id = order['changed_by_id']
    repo = get_repo(user_id)
    supplier_id = order['supplier_id']
    supplier = repo.get_supplier_by_id(supplier_id)

    return supplier


def get_distributor(order):
    user_id = order['changed_by_id']
    repo = get_repo(user_id)
    supplier_distributor_id = order['distributor_id']
    supplier_distributor = repo.get_distributor_supplier_by_supplier_distributor_id(supplier_distributor_id)

    if supplier_distributor:
        distributor_id = supplier_distributor['distributor_id']
        distributor = repo.get_distributor_by_id(distributor_id)
        return distributor

    return None


def get_user(user_id):
    repo = get_repo(user_id)

    user = repo.get_or_create_profile()

    return user


def send_email_on_purchase_order(event, context):
    logger.debug('event: {}'.format(event))
    order = json.loads(event['Records'][0]['Sns']['Message'])
    user_id = order['changed_by_id']
    entity_id = order['entity_id']

    previous_order = {}
    previous_version = order['previous_version']
    if previous_version:
        previous_order = get_previous_order(entity_id, previous_version, user_id)

    supplier = get_supplier(order)

    distributor = get_distributor(order)

    user = get_user(user_id)

    message_data = create_full_message_data(order, previous_order, supplier, user)

    to_email_list = get_to_email_list(supplier, distributor, user)

    # Send the SQS message
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=Q_NAME_EMAIL_TRANSMITTER)
    try:
        message_body = {
            "template": PO_EMAIL_TEMPLATE_NAME,
            "to": to_email_list,
            "data": message_data
            }
        print(message_body)
        response = queue.send_message(MessageBody=json.dumps(message_body))
        logger.debug('response: {}'.format(response))
    except ClientError as e:
        logger.debug('error: {}'.format(e))


def create_sample_data():
    sample_data = {
	"entity_id": "716b0fa3-bb68-434c-a9ca-d9fe924d683a",
	"order_date": 1573171200,
	"pack_date": 1574294400,
	"ship_date": 1574380800,
	"order_number": "20006",
	"po_number": None,
	"weight": 146,
	"weight_uom": "lbs",
	"number_of_pallets": 4,
	"supplier_id": "4f5b7edc-5bfe-402b-bca4-4d2397efac3c",
	"distributor_id": "09f3dcc5-505c-4b53-a745-2e7a2f8c195",
	"distributor_name": "Jay's Test",
	"user_id": "5d4a16f0eab56e0cc579da77",
	"notes": "These notes have been updated.",
	"version": "82928592-7376-4b26-a8e9-ac9faba3495c",
	"products": [{
		"brand_name": "Silver",
		"brand_id": "c19148e4-d138-4c7c-bffa-0511ba762148",
		"brandProducts": [{
			"package_type_id": "ba895b6f-9810-4c48-ae49-ecd1c4b3f0ca",
			"quantity": 2,
			"product_id": "cdccb224-8d23-4d6c-85e3-7d228b0a69cd",
			"brand_id": "c19148e4-d138-4c7c-bffa-0511ba762148",
			"package_type_name": "Case of 72 4liter Bottles",
			"ordinal": 2
		}, {
			"package_type_id": "9c015c41-7dee-44e8-94e5-bed2fc7f9eb9",
			"quantity": 3,
			"product_id": "f5700972-c31a-4ba6-95d0-7749d7cf09f4",
			"brand_id": "c19148e4-d138-4c7c-bffa-0511ba762148",
			"package_type_name": "Case of 40 6oz Cans",
			"ordinal": 3
		}]
	}],
	"merchandise": [],
	"active": False,
	"previous_version": "331c41d4-9c82-494b-8398-7baa91bb7b20",
	"latest": True,
	"changed_by_id": "5d4a16f0eab56e0cc579da77",
	"changed_on": 1573242584
}
    return sample_data


def create_previous_sample_data():
    sample_data = {
	"entity_id": "716b0fa3-bb68-434c-a9ca-d9fe924d683a",
	"order_date": 1573171200,
	"pack_date": 1574294400,
	"ship_date": 1574380800,
	"order_number": "20006",
	"po_number": None,
	"weight": 146,
	"weight_uom": "lbs",
	"number_of_pallets": 4,
	"supplier_id": "4f5b7edc-5bfe-402b-bca4-4d2397efac3c",
	"distributor_id": "09f3dcc5-505c-4b53-a745-2e7a2f8c195",
	"distributor_name": "Jay's Test",
	"user_id": "5dc5b0a39bae860e01b33ba6",
	"notes": None,
	"version": "82928592-7376-4b26-a8e9-ac9faba3495c",
	"products": [{
		"brand_name": "Iron",
		"brand_id": "10e6f7e3-8e68-4a13-b800-b6ade033b57f",
		"brandProducts": [{
			"package_type_id": "26b932a7-7742-401e-a75e-30db160a5a27",
			"quantity": 6,
			"product_id": "4963b39f-9154-4679-a7a8-3df7b1a6735f",
			"brand_id": "10e6f7e3-8e68-4a13-b800-b6ade033b57f",
			"package_type_name": "Case of 16 500ml Cans",
			"ordinal": 0
		}, {
			"package_type_id": "eb4328f2-1c67-48ac-bc26-b5c127d48765",
			"quantity": 0,
			"product_id": "44877e7d-8aab-4a74-b32f-ac644c7b97c6",
			"brand_id": "10e6f7e3-8e68-4a13-b800-b6ade033b57f",
			"package_type_name": "Case of 20 12.5gal Kegs",
			"ordinal": 1
		}, {
			"package_type_id": "ba895b6f-9810-4c48-ae49-ecd1c4b3f0ca",
			"quantity": 2,
			"product_id": "22ff6335-61eb-435c-ace1-2e8e2d4e8b1b",
			"brand_id": "10e6f7e3-8e68-4a13-b800-b6ade033b57f",
			"package_type_name": "Case of 72 4liter Bottles",
			"ordinal": 2
		}]
	}],
	"merchandise": [{
		"merchandise_id": "b6a6daa0-5693-4944-b3f2-01ee3a4d4209",
		"merchandise_size_quantities": [{
			"size": "s",
			"quantity": "5"
		}, {
			"size": "m",
			"quantity": "3"
		}, {
			"size": "l",
			"quantity": "2"
		}],
		"merchandise_name": "T-Shirt"
	}],
	"active": True,
	"previous_version": "331c41d4-9c82-494b-8398-7baa91bb7b20",
	"latest": True,
	"changed_by_id": "5dc5b0a39bae860e01b33ba6",
	"changed_on": 1573242584
}
    return sample_data


if __name__ == "__main__":
    sample_order = create_sample_data()
    previous_sample_order = create_previous_sample_data()
    supplier = get_supplier(sample_order)
    distributor = get_distributor(sample_order)
    user_id = sample_order['changed_by_id']
    user = get_user(user_id)

    message = create_full_message_data(sample_order, previous_sample_order, supplier, user)
    email_list = get_to_email_list(supplier, distributor, user)

    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=Q_NAME_EMAIL_TRANSMITTER)
    try:
        message_body = {
            "template": PO_EMAIL_TEMPLATE_NAME,
            "to": email_list,
            "data": message
        }

        response = queue.send_message(MessageBody=json.dumps(message_body))
        logger.debug('response: {}'.format(response))
    except ClientError as e:
        logger.debug('error: {}'.format(e))


