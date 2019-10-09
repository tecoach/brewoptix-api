from datetime import datetime
import os
import time

import maya
from maya import MayaInterval
from boto3.dynamodb.conditions import Key, Attr
from dynamodb_json import json_util

from data_common.constants import on_hand_attributes, base_attributes
from data_common.exceptions import BadParameters, NoSuchEntity, AquireProjectionLockError
from data_common.repository import OnHandRepository
from data_common.notifications import SnsNotifier
from data_common.utils import clean
from data_dynamodb.utils import check_for_required_keys, check_properties_datatypes


class DynamoOnHandRepository(OnHandRepository, SnsNotifier):
    def get_all_on_hands(self, supplier_id):
        obj_type = 'on-hand-inventory'

        query = {
            'KeyConditionExpression': Key('supplier_id').eq(supplier_id) & Key('obj_type').eq(obj_type),
            'FilterExpression':
                (Attr('latest').eq(True) & Attr('active').eq(True)),
            'IndexName': 'by_supplier_id_and_obj_type'
        }

        response = self._storage.get_items(query)

        on_hands_obj = []

        for item in response['Items']:
            # The 4 lines below can be uncommented if we move
            # from ALL to KEYS_ONLY for the table
            # entity_id = item['EntityID']
            # on_hand = self._storage.get(table, entity_id)
            # on_hand = clean(on_hand)
            on_hand = json_util.loads(clean(item))
            on_hand['observation_date'] = maya.to_iso8601(
                datetime.utcfromtimestamp(
                    on_hand['observation_date']
                )
            ).split('T')[0]
            on_hands_obj.append(on_hand)

        return on_hands_obj

    def save_on_hand(self, obj):
        obj_type = 'on-hand-inventory'

        check_for_required_keys(obj, on_hand_attributes)
        content = {k: v for k, v in obj.items() if k not in base_attributes}
        check_properties_datatypes(content, on_hand_attributes)

        obj['user_id'] = self._user_id

        obj['observation_date'] = maya.parse(
            obj['observation_date']).epoch

        on_hand_obj = self._storage.save(obj_type, obj)
        self.sns_publish("on-hand", obj)  # publish notification

        on_hand = clean(on_hand_obj)
        on_hand['observation_date'] = datetime.utcfromtimestamp(
            on_hand['observation_date']
        ).isoformat().split('T')[0]

        return on_hand

    def get_on_hand_record_by_id(self, supplier_id, entity_id):
        obj_type = 'on-hand-inventory'

        on_hand = self._storage.get(entity_id)
        if on_hand:
            on_hand = clean(on_hand)

            if on_hand["supplier_id"] != supplier_id:
                raise NoSuchEntity

            on_hand['observation_date'] = datetime.utcfromtimestamp(
                on_hand['observation_date']
            ).isoformat().split('T')[0]
        else:
            raise NoSuchEntity

        return on_hand

    def delete_on_hand_record_by_id(self, supplier_id, entity_id):
        obj_type = 'on-hand-inventory'

        on_hand = self._storage.get(entity_id)

        if on_hand:
            obj = clean(on_hand)

            if obj["supplier_id"] != supplier_id:
                raise NoSuchEntity

            obj["active"] = False
            self._storage.save(obj_type, obj)
            self.sns_publish("on-hand", obj)  # publish notification
        else:
            raise NoSuchEntity

    def _acquire_lock(self, brand_id, package_type_id, request_id):
        print('Acquire lock for brand_id: {}, '
              'package_type_id: {}, request_id: {}'.format(brand_id,
                                                           package_type_id,
                                                           request_id))
        table = 'projection_locks'
        for attempt in range(0, 11):
            time.sleep(2 * attempt)
            item = {
                "brand_id": brand_id,
                "package_type_id": package_type_id,
                "request_id": request_id,
                "timestamp": int(time.time())
            }

            try:
                obj = self._aurora_storage.save(table, item)
                break
            except Exception:
                pass
        else:
            raise AquireProjectionLockError("Timeout")

        print(obj)
        return obj

    def _release_lock(self, brand_id, package_type_id):
        print('Release lock for brand_id: {}, package_type_id: {}'.format(brand_id, package_type_id))
        table = 'projection_locks'
        query = """
                DELETE
                FROM {TABLE}
                WHERE package_type_id='{PACKAGE_TYPE_ID}' AND brand_id='{BRAND_ID}'
                """.format(TABLE=table,
                           BRAND_ID=brand_id,
                           PACKAGE_TYPE_ID=package_type_id)

        resp = self._aurora_storage._execute(query)
        print(resp)
        return resp

    def process_projections_queue(self, supplier_id, brand_id, package_type_id, start_date, request_id):
        try:
            self._acquire_lock(brand_id, package_type_id, request_id)

            print(brand_id, package_type_id, start_date)
            start_date_minus_one = maya.parse(start_date).add(days=-1).iso8601().split('T')[0]

            cutoff = int(os.environ['PROJECTIONS_CUTOFF_DELTA_DAYS'])
            end_date = maya.when('today').add(days=cutoff).iso8601().split('T')[0]

            # query on_hand between start date minus 1 and end date
            table = 'on_hand'
            query = """
            SELECT *
            FROM {TABLE}
            USE INDEX (by_created_on_and_supplier_id)
            WHERE supplier_id='{SUPPLIER_ID}' AND package_type_id='{PACKAGE_TYPE_ID}' AND brand_id='{BRAND_ID}' AND (created_on BETWEEN '{START_DATE}' AND '{END_DATE}') 
            """.format(TABLE=table,
                       SUPPLIER_ID=supplier_id,
                       START_DATE=start_date_minus_one,
                       END_DATE=end_date,
                       BRAND_ID=brand_id,
                       PACKAGE_TYPE_ID=package_type_id)
            results = self._aurora_storage.get_items(query)

            # # convert from response
            keys = [
                "supplier_id",
                "created_on",
                "brand_id",
                "package_type_id",
                "quantity",
                "actual"
            ]

            on_hands_theoretical = {}
            on_hands_actual = {}
            for result in results:
                record = {}
                for i, val in enumerate(result):
                    record[keys[i]] = val

                if record['actual']:
                    on_hands_actual[record['created_on']] = record
                else:
                    on_hands_theoretical[record['created_on']] = record

            print("On Hand: ")
            print(on_hands_actual)
            print(on_hands_theoretical)

            # query productions between start date and end date
            table = 'production'
            query = """
                    SELECT production_date, SUM(quantity)
                    FROM {TABLE}
                    USE INDEX (by_production_date_and_supplier_id)
                    WHERE supplier_id='{SUPPLIER_ID}' AND package_type_id='{PACKAGE_TYPE_ID}' AND brand_id='{BRAND_ID}' AND (production_date BETWEEN '{START_DATE}' AND '{END_DATE}') 
                    GROUP BY production_date
                    """.format(TABLE=table,
                               SUPPLIER_ID=supplier_id,
                               START_DATE=start_date,
                               END_DATE=end_date,
                               BRAND_ID=brand_id,
                               PACKAGE_TYPE_ID=package_type_id)
            results = self._aurora_storage.get_items(query)

            # # convert from response
            keys = [
                "production_date",
                "quantity"
            ]

            production = {}
            for result in results:
                record = {}
                for i, val in enumerate(result):
                    record[keys[i]] = val

                production[record['production_date']] = record

            print("Production: ")
            print(production)

            # query sales between start date and end date
            table = 'sales'
            query = """
                    SELECT sale_date, SUM(quantity)
                    FROM {TABLE}
                    USE INDEX (by_sale_date_and_supplier_id)
                    WHERE supplier_id='{SUPPLIER_ID}' AND package_type_id='{PACKAGE_TYPE_ID}' AND brand_id='{BRAND_ID}' AND (sale_date BETWEEN '{START_DATE}' AND '{END_DATE}') 
                    GROUP BY sale_date
                    """.format(TABLE=table,
                               SUPPLIER_ID=supplier_id,
                               START_DATE=start_date,
                               END_DATE=end_date,
                               BRAND_ID=brand_id,
                               PACKAGE_TYPE_ID=package_type_id)
            results = self._aurora_storage.get_items(query)

            # # convert from response
            keys = [
                "sale_date",
                "quantity"
            ]

            sales = {}
            for result in results:
                record = {}
                for i, val in enumerate(result):
                    record[keys[i]] = val

                sales[record['sale_date']] = record

            print("Sales: ")
            print(sales)

            # query adjustments between start date and end date
            table = 'adjustments'
            query = """
                    SELECT adjustment_date, SUM(quantity)
                    FROM {TABLE}
                    USE INDEX (by_adjustment_date_and_supplier_id)
                    WHERE supplier_id='{SUPPLIER_ID}' AND package_type_id='{PACKAGE_TYPE_ID}' AND brand_id='{BRAND_ID}' AND (adjustment_date BETWEEN '{START_DATE}' AND '{END_DATE}') 
                    GROUP BY adjustment_date
                    """.format(TABLE=table,
                               SUPPLIER_ID=supplier_id,
                               START_DATE=start_date,
                               END_DATE=end_date,
                               BRAND_ID=brand_id,
                               PACKAGE_TYPE_ID=package_type_id)
            results = self._aurora_storage.get_items(query)

            # # convert from response
            keys = [
                "adjustment_date",
                "quantity"
            ]

            adjustments = {}
            for result in results:
                record = {}
                for i, val in enumerate(result):
                    record[keys[i]] = val

                adjustments[record['adjustment_date']] = record

            print("Adjustments: ")
            print(adjustments)

            start = maya.parse(start_date)
            end = maya.parse(end_date)
            interval = MayaInterval(start=start, end=end)

            objs = []
            for day_interval in interval.split(duration=24*60*60):
                current_date = day_interval.start.iso8601().split('T')[0]
                previous_date = maya.parse(current_date).add(days=-1).iso8601().split('T')[0]

                if previous_date in on_hands_actual:
                    start_quantity = on_hands_actual[previous_date]['quantity']
                elif previous_date in on_hands_theoretical:
                    start_quantity = on_hands_theoretical[previous_date]['quantity']
                else:
                    start_quantity = 0

                produce = 0
                if current_date in production:
                    produce = production[current_date]['quantity']

                sale_quantity = 0
                if current_date in sales:
                    sale_quantity = sales[current_date]['quantity']

                adjust_quantity = 0
                if current_date in adjustments:
                    adjust_quantity = adjustments[current_date]['quantity']

                quantity = int(start_quantity) + int(produce) - int(sale_quantity) + int(adjust_quantity)

                if current_date in on_hands_actual:
                    # we don't want to disturb the actual entries, we are only going to manipulate theoretical entries
                    pass
                else:
                    obj = {
                        'supplier_id': supplier_id,
                        'created_on': current_date,
                        'brand_id': brand_id,
                        'package_type_id': package_type_id,
                        'quantity': quantity,
                        'actual': False
                    }
                    objs.append(obj)

                    # update
                    on_hands_theoretical[current_date] = obj

            # Delete all actual=False entries in on_hand in this time period
            table = 'on_hand'
            query = """
                    DELETE
                    FROM {TABLE}
                    WHERE supplier_id='{SUPPLIER_ID}' AND package_type_id='{PACKAGE_TYPE_ID}' AND brand_id='{BRAND_ID}' AND actual=false AND (created_on BETWEEN '{START_DATE}' AND '{END_DATE}') 
                    """.format(TABLE=table,
                               SUPPLIER_ID=supplier_id,
                               START_DATE=start_date,
                               END_DATE=end_date,
                               BRAND_ID=brand_id,
                               PACKAGE_TYPE_ID=package_type_id)
            resp = self._aurora_storage._execute(query)
            print(resp)

            # Insert into on_hand
            resp = self._aurora_storage.bulk_insert('on_hand', objs)
            print(resp)

            obj = {
                "supplier_id": supplier_id,
                "brand_id": brand_id,
                "package_type_id": package_type_id,
                "start_date": start_date,
                "end_date": end_date
            }
            self.sns_publish("projections", obj)  # publish notification

        finally:
            self._release_lock(brand_id, package_type_id)

    def get_details_by_date_range(self, supplier_id, start_date, end_date=None):
        # query on_hand between start date minus 1 and end date
        start_date = maya.parse(start_date).iso8601().split('T')[0]
        end_date = maya.parse(end_date).iso8601().split('T')[0]

        table = 'on_hand'
        offset = 0
        count = 1000
        details = []

        while True:
            query = """
                        SELECT created_on, brand_id, package_type_id, quantity, actual
                        FROM {TABLE}
                        WHERE  supplier_id='{SUPPLIER_ID}' AND (created_on BETWEEN '{START_DATE}' AND '{END_DATE}') AND (quantity<>0)
                        ORDER BY brand_id, package_type_id, created_on, actual
                        LIMIT {OFFSET}, {COUNT}
                        """.format(TABLE=table,
                                   SUPPLIER_ID=supplier_id,
                                   START_DATE=start_date,
                                   END_DATE=end_date,
                                   OFFSET=offset,
                                   COUNT=count)

            results = self._aurora_storage.get_items(query)

            # convert from response
            keys = [
                "created_on",
                "brand_id",
                "package_type_id",
                "quantity",
                "actual"
            ]

            for result in results:
                record = {}
                for i, val in enumerate(result):
                    record[keys[i]] = val

                if record['actual']:
                    record['actual'] = False
                details.append(record)

            if len(results) < 1000:
                break
            else:
                offset += 1000

        return details
