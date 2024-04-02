
# PyJWT==2.4.0 <----
# jwt==1.3.1

# from jwt import (
#     JWT,
#     jwk_from_dict,
#     jwk_from_bytes,
# )
import jwt, json

import requests
import os
from libs.commonlib.db_insist import get_db


REACT_APP_JWT_SECRET  = os.getenv('REACT_APP_JWT_SECRET', '')
ALWAYS_LET_ME_IN      = os.getenv('ALWAYS_LET_ME_IN', 'false') == 'true'

#
# Vipps stuff :
#
VIPPS_PUBLIC_KEYS_URI        = os.getenv('VIPPS_PUBLIC_KEYS_URI', '')
VIPPS_CLIENT_ID              = os.getenv('VIPPS_CLIENT_ID' , '')
VIPPS_CLIENT_SECRET          = os.getenv('VIPPS_CLIENT_SECRET' , '')
VIPPS_SUBSCRIPTION_KEY       = os.getenv('VIPPS_SUBSCRIPTION_KEY', '')
VIPPS_MERCHANT_SERIAL_NUMBER = os.getenv('VIPPS_MERCHANT_SERIAL_NUMBER', '')
VIPPS_BASE_URL               = os.getenv('VIPPS_BASE_URL', '')
VIPPS_ACCESS_TOKEN           = VIPPS_BASE_URL + 'accesstoken/get'

def vippsecomkey() -> str :

    url = VIPPS_ACCESS_TOKEN
    headers = {
        'client_id'                : VIPPS_CLIENT_ID,
        'client_secret'            : VIPPS_CLIENT_SECRET,
        'Ocp-Apim-Subscription-Key': VIPPS_SUBSCRIPTION_KEY,
        'Merchant-Serial-Number'   : VIPPS_MERCHANT_SERIAL_NUMBER
    }
    response = requests.post(url, headers=headers, json=None)
    response_json = response.json()
    return response_json.get('access_token' , '')

def verify_vipps_id_token(req) -> str:

    def verify_signature(token, key : dict) -> dict:
        try:
            hdr = jwt.get_unverified_header(token)
            if hdr.get('kid', '_') != key.get('kid', ''):
                return {}
            if hdr.get('alg', '_') != key.get('alg', ''):
                return {}
            verifying_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            return jwt.decode(token, key=verifying_key, algorithms=[key['alg']], audience=VIPPS_CLIENT_ID)
        except Exception as e:
            return {}

    auth_header = decode_auth_header(req)
    if not auth_header or not 'id_token' in auth_header or not 'access_token' in auth_header:
        return ''
    id_token = auth_header['id_token']
    if not id_token:
        print('verify_token :: Failed, nothing found in Authorization HTTP header')
        return ''
    vipps_ret = requests.get(VIPPS_PUBLIC_KEYS_URI)
    vipps_ret_json = vipps_ret.json()
    keys = vipps_ret_json.get('keys' , [])
    for key in keys :
        message = verify_signature(id_token, key)
        if message and message['iss'] in VIPPS_PUBLIC_KEYS_URI:
            return auth_header['access_token']
    return ''

def decode_auth_header(req) :
    # TODO ##############
    # TODO
    # TODO : We are using symmetric signature HS256, which is not the most secure (but its faster). Should switch to assymetric
    # TODO   with RS256, using a public+private key.
    # TODO
    # TODO  NOTE : Signing IS NOT encryption, so don't lean on it for security, only for data integrity
    # TODO
    # TODO ##############
    access_token = req.headers.get('Authorization', "")
    if not access_token :
        print('verify_token :: Failed, nothing found in Authorization HTTP header')
        return {}
    try :
        return jwt.decode(access_token, REACT_APP_JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        return {}

def let_me_in(decoded_jwt : dict, db = get_db(), DEBUG_USER = None) -> bool :
    if ALWAYS_LET_ME_IN == True :
        if DEBUG_USER:
            decoded_jwt['phone'] = DEBUG_USER.get('phone', DEBUG_USER.get('phone_number' , decoded_jwt.get('phone' , '')))
            decoded_jwt['email'] = DEBUG_USER.get('email', DEBUG_USER.get('email_address', decoded_jwt.get('email', '')))
            decoded_jwt['firstname'] = DEBUG_USER.get('firstname' , '')
            decoded_jwt['lastname'] = DEBUG_USER.get('lastname', '')
            decoded_jwt['location_name'] = DEBUG_USER.get('location_name', '')
        return True
    try:
        access_token = decoded_jwt.get('access_token' , '')
        phone = decoded_jwt.get('phone' , '')
        if not access_token or not phone:
            return False

        if DEBUG_USER :
            phone = DEBUG_USER.get('phone' , phone)

        confirmed_token = db.insist_on_find_one_q('access_tokens' , {'num' : phone})
        return confirmed_token and confirmed_token['access_token'] == access_token
    except Exception as e:
        return False


