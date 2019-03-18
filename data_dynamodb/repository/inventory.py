from datetime import datetime, timedelta

import maya

from data_common.repository import InventoryRepository


class AuroraInventoryRepository(InventoryRepository):
    def get_inventory_products_by_date_range(self, supplier_id, start_date, end_date=None):
        start_date = datetime.utcfromtimestamp(maya.parse(start_date.split('T')[0]).epoch)
        on_hand_start_date = start_date - timedelta(days=1)

        start_date = start_date.isoformat().split('T')[0]
        on_hand_start_date = on_hand_start_date.isoformat().split('T')[0]

        if end_date:
            end_date = datetime.utcfromtimestamp(maya.parse(end_date.split('T')[0]).epoch).isoformat().split('T')[0]
        else:
            end_date = datetime.utcfromtimestamp(maya.now().epoch).isoformat().split('T')[0]

        inventory = {}

        # ON HAND START
        query = """SELECT brand_id, package_type_id, quantity as on_hand_start
        FROM on_hand
        WHERE supplier_id = '{SUPPLIER_ID}' AND created_on = '{START_DATE}'"""

        query = query.format(SUPPLIER_ID=supplier_id, START_DATE=on_hand_start_date)

        print(query)

        results = self._aurora_storage.get_items(query)

        # # convert from response
        keys = [
            "brand_id",
            "package_type_id",
            "on_hand_start"
        ]

        records = []
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            records.append(record)

        for r in records:
            _id = r['brand_id'] + '_' + r['package_type_id']
            if _id in inventory:
                inventory[_id]['on_hand_start'] = r['on_hand_start']
            else:
                inventory[_id] = {
                    'supplier_id': supplier_id,
                    'brand_id': r['brand_id'],
                    'package_type_id': r['package_type_id'],
                    'on_hand_start': r['on_hand_start'],
                    'produced': 0,
                    'adjustments': 0,
                    'on_hand_end': 0,
                    'sales': 0,
                }

        # ON HAND END
        query = """SELECT brand_id, package_type_id, quantity as on_hand_end
        FROM on_hand
        WHERE supplier_id = '{SUPPLIER_ID}' AND created_on = '{END_DATE}'"""

        query = query.format(SUPPLIER_ID=supplier_id, END_DATE=end_date)

        print(query)

        results = self._aurora_storage.get_items(query)

        # # convert from response
        keys = [
            "brand_id",
            "package_type_id",
            "on_hand_end"
        ]

        records = []
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            records.append(record)

        for r in records:
            _id = r['brand_id'] + '_' + r['package_type_id']
            if _id in inventory:
                inventory[_id]['on_hand_end'] = r['on_hand_end']
            else:
                inventory[_id] = {
                    'supplier_id': supplier_id,
                    'brand_id': r['brand_id'],
                    'package_type_id': r['package_type_id'],
                    'on_hand_end': r['on_hand_end'],
                    'produced': 0,
                    'adjustments': 0,
                    'on_hand_start': 0,
                    'sales': 0,
                }

        # PRODUCED
        query = """SELECT brand_id, package_type_id, IFNULL(SUM(quantity), 0) AS produced
        FROM production
        WHERE supplier_id = '{SUPPLIER_ID}' AND production_date BETWEEN '{START_DATE}' AND '{END_DATE}'
        GROUP BY brand_id, package_type_id""".format(SUPPLIER_ID=supplier_id,
                                                     START_DATE=start_date,
                                                     END_DATE=end_date)
        print(query)

        results = self._aurora_storage.get_items(query)

        # convert from response
        keys = [
            "brand_id",
            "package_type_id",
            "produced"
        ]

        records = []
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            records.append(record)

        for r in records:
            _id = r['brand_id'] + '_' + r['package_type_id']
            if _id in inventory:
                inventory[_id]['produced'] = r['produced']
            else:
                inventory[_id] = {
                    'supplier_id': supplier_id,
                    'brand_id': r['brand_id'],
                    'package_type_id': r['package_type_id'],
                    'produced': r['produced'],
                    'adjustments': 0,
                    'on_hand_end': 0,
                    'on_hand_start': 0,
                    'sales': 0,
                }

        # SALES
        query = """SELECT brand_id, package_type_id, IFNULL(SUM(quantity), 0) AS sales
        FROM sales
        WHERE supplier_id = '{SUPPLIER_ID}' AND sale_date BETWEEN '{START_DATE}' AND '{END_DATE}'
        GROUP BY brand_id, package_type_id""".format(SUPPLIER_ID=supplier_id,
                                                     START_DATE=start_date,
                                                     END_DATE=end_date)

        print(query)

        results = self._aurora_storage.get_items(query)

        # # convert from response
        keys = [
            "brand_id",
            "package_type_id",
            "sales"
        ]

        records = []
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            records.append(record)

        for r in records:
            _id = r['brand_id'] + '_' + r['package_type_id']
            if _id in inventory:
                inventory[_id]['sales'] = r['sales']
            else:
                inventory[_id] = {
                    'supplier_id': supplier_id,
                    'brand_id': r['brand_id'],
                    'package_type_id': r['package_type_id'],
                    'sales': r['sales'],
                    'adjustments': 0,
                    'on_hand_end': 0,
                    'on_hand_start': 0,
                    'produced': 0
                }

        # ADJUSTMENTS
        query = """SELECT brand_id, package_type_id, IFNULL(SUM(quantity), 0) AS adjustments
                FROM adjustments
                WHERE supplier_id = '{SUPPLIER_ID}' AND adjustment_date BETWEEN '{START_DATE}' AND '{END_DATE}'
                GROUP BY brand_id, package_type_id""".format(SUPPLIER_ID=supplier_id,
                                                             START_DATE=start_date,
                                                             END_DATE=end_date)

        print(query)

        results = self._aurora_storage.get_items(query)

        # # convert from response
        keys = [
            "brand_id",
            "package_type_id",
            "adjustments"
        ]

        records = []
        for result in results:
            record = {}
            for i, val in enumerate(result):
                record[keys[i]] = val
            records.append(record)

        for r in records:
            _id = r['brand_id'] + '_' + r['package_type_id']
            if _id in inventory:
                inventory[_id]['adjustments'] = r['adjustments']
            else:
                inventory[_id] = {
                    'supplier_id': supplier_id,
                    'brand_id': r['brand_id'],
                    'package_type_id': r['package_type_id'],
                    'adjustments': r['adjustments'],
                    'on_hand_end': 0,
                    'on_hand_start': 0,
                    'sales': 0,
                    'produced': 0
                }

        items = list(inventory.values())

        return items
