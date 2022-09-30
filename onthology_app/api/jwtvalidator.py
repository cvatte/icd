from flask import request
from flask import Response
import jwt
#from jwksutils import rsa_pem_from_jwk
import json
import requests
import base64
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization



jwks = {}

valid_audiences = []  # id of the application prepared previously

issuer = 'https://sts.windows.net/aed9d8d6-b4be-478d-a113-58633a7e611f/'


class InvalidAuthorizationToken(Exception):
    def __init__(self, details):
        super().__init__('Invalid authorization token: ' + details)


# jwt.get_unverified header goes away in PyJWT 1.7.x
def getUnverifiedHeader(token):
    jwts = token.split('.')
    return json.loads(base64.b64decode(jwts[0] + '==').decode("utf-8"))


def get_jwt_value(token, key):
    headers = getUnverifiedHeader(token)  # jwt.get_unverified_header(token)
    if not headers:
        raise InvalidAuthorizationToken('missing headers')
    try:
        return headers[key]
    except KeyError:
        raise InvalidAuthorizationToken('missing ' + key)


def get_kid(token):
    headers = getUnverifiedHeader(token)  # jwt.get_unverified_header(token)
    if not headers:
        raise InvalidAuthorizationToken('missing headers')
    try:
        return headers['kid']
    except KeyError:
        raise InvalidAuthorizationToken('missing kid')


def get_alg(token):
    headers = getUnverifiedHeader(token)  # jwt.get_unverified_header(token)
    if not headers:
        raise InvalidAuthorizationToken('missing headers')
    try:
        return headers['alg']
    except KeyError:
        raise InvalidAuthorizationToken('missing alg')


def get_jwk(kid):
    for jwk in jwks['keys']:
        if jwk['kid'] == kid:
            return jwk
    raise InvalidAuthorizationToken('kid not recognized')

#################################################################################################

def rsa_pem_from_jwk(jwk):
    return RSAPublicNumbers(
        n=decode_value(jwk['n']),
        e=decode_value(jwk['e'])
    ).public_key(default_backend()).public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def ensure_bytes(key):
    if isinstance(key, str):
        key = key.encode('utf-8')
    return key


def decode_value(val):
    decoded = base64.urlsafe_b64decode(ensure_bytes(val) + b'==')
    return int.from_bytes(decoded, 'big')

###################################################################################################

def get_public_key(token):
    return rsa_pem_from_jwk(get_jwk(get_kid(token)))


def validate_jwt(jwt_to_validate):
    alg = get_alg(jwt_to_validate)  # RS256
    public_key = get_public_key(jwt_to_validate)

    jwt_decoded = jwt.decode(jwt_to_validate,
                             public_key,
                             verify=True,
                             algorithms=[alg],
                             audience=valid_audiences,
                             issuer=issuer)

    # do what you wish with decoded token:
    # if we get here, the JWT is validated
    return jwt_decoded


def initWellKnownConfig(urlWellKnown):

    global issuer
    # get the well known info & get the public keys
    resp = requests.get(url=urlWellKnown)

    well_known_openid_config_data = resp.json()
    jwks_uri = well_known_openid_config_data['jwks_uri']
    issuer = well_known_openid_config_data['issuer']
    # get the discovery keys
    resp = requests.get(url=jwks_uri)
    jwks.update(resp.json())


def initAzureAD(tenantId, clientId):

    global issuer
    global valid_audiences
    valid_audiences.append(clientId)

    initWellKnownConfig('https://login.microsoftonline.com/' + tenantId + '/v2.0/.well-known/openid-configuration')
    issuer = "https://sts.windows.net/" + tenantId + "/"


def initAuthority(wellKnownMetadataEndpoint, clientId):
    global issuer
    valid_audiences.append(clientId)
    initWellKnownConfig(wellKnownMetadataEndpoint)


def checkAuthorization(requiredScopes=None):
    # Authorization: Bearer AbCdEf123456
    accessKeyName = "Authorization"
    passedAccessKey = ""
    if accessKeyName in request.headers:
        passedAccessKey = request.headers[accessKeyName]

    if not passedAccessKey.startswith("Bearer "):
        msg = {"message": 'Unauthorized. No or wrong token received in request',"statusCode" : "107"}
        return None, Response(json.dumps(msg), status=401, mimetype='application/json')

    jwt_decoded = None
    try:
        jwt_decoded = validate_jwt(passedAccessKey[7:])
    except Exception as ex:
        msg = {"message": 'Unauthorized. Token is invalid. ' + ex.args[0],"statusCode" : "106"}
        return None, Response(json.dumps(msg), status=401, mimetype='application/json')
    else:
        if requiredScopes is not None and len(requiredScopes) > 0:
            jwtScopes = jwt_decoded['scp'].split()
            if not requiredScopes in jwtScopes:
                msg = {"message": 'Unauthorized. Required scope(s) missing: ' + requiredScopes,"statusCode" : "108"}
                return None, Response(json.dumps(msg), status=403, mimetype='application/json')

        return jwt_decoded, None