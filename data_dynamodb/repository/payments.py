import os
import uuid

import maya
import stripe

from data_common.repository import PaymentsRepository


class DynamoPaymentsRepository(PaymentsRepository):
    def charge_by_stripe(self, obj):    # noqa: C901
        obj_type = 'payments'

        stripe.api_key = os.environ['STRIPE_SECRET_KEY']

        # creating payment entity before charging
        obj['entity_id'] = str(uuid.uuid4())
        obj['provider'] = 'stripe'
        # obj['status'] = 'initiating'
        obj['timestamp'] = maya.now().epoch
        obj['description'] = \
            'BrewOptix Subscription for {PLAN}'.format(PLAN=obj['plan_level'])
        obj['secrets'] = {
            'source': obj['source']
        }

        # payment_obj = self._storage.save(table, obj)

        try:
            # Charge the user
            charge = stripe.Charge.create(
                amount=obj['amount'],
                currency=obj['currency'],
                description=obj['description'],
                source=obj['source'],  # obtained with Stripe.js
                idempotency_key=obj['entity_id'],
                metadata={
                    'order_id': obj['entity_id']
                }
            )
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error', {})

            error_msg = err.get('message')
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            body = e.json_body
            err = body.get('error', {})

            error_msg = err.get('message')
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            body = e.json_body
            err = body.get('error', {})

            error_msg = err.get('message')
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            body = e.json_body
            err = body.get('error', {})

            error_msg = err.get('message')
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            body = e.json_body
            err = body.get('error', {})

            error_msg = err.get('message')
        except Exception:
            error_msg = 'Unknown error'

        if 'charge' in locals() and charge['status'] == 'succeeded':
            status = 'succeeded'
            obj['secrets']['charge_id'] = charge['id']
        elif 'charge' in locals() and 'status' in charge:
            status = charge['status']
        else:
            status = 'failed'

        obj['status'] = status
        obj['user_id'] = self._user_id

        obj.pop('source')
        payment_obj = self._storage.save(obj_type, obj)

        resp = {
            'status': obj['status']
        }
        if obj['status'] == 'succeeded':
            resp['charge_id'] = charge['id']
        else:
            resp['error'] = error_msg

        return resp

    def get_all_payments(self):
        pass
