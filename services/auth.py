import os

from jose import jwt
# from cryptography.hazmat.backends import default_backend
# from cryptography import x509

AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_PUBLIC_KEY = os.getenv('AUTH0_CLIENT_PUBLIC_KEY')


def auth(event, context):
    whole_auth_token = event.get('authorizationToken')
    if not whole_auth_token:
        raise Exception('Unauthorized')

    print('Client token: ' + whole_auth_token)
    print('Method ARN: ' + event['methodArn'])

    token_parts = whole_auth_token.split(' ')
    auth_token = token_parts[1]
    token_method = token_parts[0]

    if not (token_method.lower() == 'bearer' and auth_token):
        print('Failing due to invalid token_method or missing auth_token')
        raise Exception('Unauthorized')

    try:
        print(AUTH0_CLIENT_ID)
        print(AUTH0_CLIENT_PUBLIC_KEY)
        principal_id = jwt_verify(auth_token, AUTH0_CLIENT_PUBLIC_KEY)
        arn = event['methodArn']
        for request_type in ['GET', 'POST', 'PUT', 'DELETE']:
            slug = '/' + request_type + '/'
            if slug in arn:
                arn = arn.split(slug)[0]

        arn += '/*'
        policy = generate_policy(principal_id, 'Allow', arn)
        return policy
    except Exception as e:
        print(f'Exception encountered: {e}')
        raise Exception('Unauthorized')


def jwt_decode(auth_token, public_key):
    public_key = format_public_key(public_key)
    print(public_key)
    # pub_key = convert_certificate_to_pem(public_key)
    # print(pub_key)
    payload = jwt.decode(auth_token, public_key, algorithms=['RS256'],
                         audience=AUTH0_CLIENT_ID)
    print(payload)
    return payload


def jwt_encode(claims, public_key):
    public_key = format_public_key(public_key)
    print(public_key)
    # pub_key = convert_certificate_to_pem(public_key)
    # print(pub_key)
    token = jwt.encode(claims, public_key, algorithm='RS256')
    print(token)
    return token


def jwt_verify(auth_token, public_key):
    public_key = format_public_key(public_key)
    print(public_key)
    # pub_key = convert_certificate_to_pem(public_key)
    # print(pub_key)
    payload = jwt.decode(auth_token, public_key,
                         algorithms=['RS256'], audience=AUTH0_CLIENT_ID)
    return payload['sub']


def generate_policy(principal_id, effect, resource):
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource

                }
            ]
        }
    }


# def convert_certificate_to_pem(public_key):
#     cert_str = public_key.encode()
#     cert_obj = x509.load_pem_x509_certificate(cert_str, default_backend())
#     pub_key = cert_obj.public_key()
#     return pub_key


def format_public_key(public_key):
    public_key = public_key.replace('\n', ' ').replace('\r', '')
    public_key = public_key.replace('-----BEGIN CERTIFICATE-----',
                                    '-----BEGIN CERTIFICATE-----\n')
    public_key = public_key.replace('-----END CERTIFICATE-----',
                                    '\n-----END CERTIFICATE-----')
    return public_key
