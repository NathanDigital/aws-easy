"""
Let's Encrypt ACME client for Lambda.
Generates and renews TLS certificates using DNS-01 challenge via Route53.
"""

import boto3
import json
import os
import time
import hashlib
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Let's Encrypt production directory
ACME_DIRECTORY = 'https://acme-v02.api.letsencrypt.org/directory'


def handler(event, context):
    """Handle EventBridge (renewal) or API Gateway (cert download) invocations."""

    # API Gateway request - return certificate
    if 'requestContext' in event and 'http' in event.get('requestContext', {}):
        return handle_api_request(event)

    # EventBridge or Custom Resource - generate/renew certificate
    if event.get('RequestType'):
        # CloudFormation custom resource
        return handle_cfn_request(event, context)

    # EventBridge scheduled event
    return generate_certificate()


def handle_api_request(event):
    """Handle GET /cert requests - return certificate from Secrets Manager."""
    auth_header = event.get('headers', {}).get('authorization', '')
    expected_token = os.environ.get('CERT_TOKEN', '')

    if not auth_header.startswith('Bearer ') or auth_header[7:] != expected_token:
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'Invalid authorization'})
        }

    # Retrieve certificate from Secrets Manager
    try:
        secrets = boto3.client('secretsmanager')
        response = secrets.get_secret_value(SecretId=os.environ['CERT_SECRET_ARN'])
        cert_data = json.loads(response['SecretString'])

        # Don't return the account key to clients
        cert_data.pop('account_key', None)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(cert_data)
        }
    except secrets.exceptions.ResourceNotFoundException:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Certificate not yet generated'})
        }
    except Exception as e:
        print(f"ERROR retrieving certificate: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to retrieve certificate'})
        }


def handle_cfn_request(event, context):
    """Handle CloudFormation custom resource requests."""
    import urllib.request

    response_data = {}
    status = 'SUCCESS'
    reason = ''

    try:
        if event['RequestType'] in ('Create', 'Update'):
            result = generate_certificate()
            if result.get('statusCode', 200) != 200:
                status = 'FAILED'
                reason = result.get('body', 'Certificate generation failed')
    except Exception as e:
        status = 'FAILED'
        reason = str(e)
        print(f"ERROR in CFN handler: {e}")

    # Send response to CloudFormation
    response_body = json.dumps({
        'Status': status,
        'Reason': reason or 'See CloudWatch logs',
        'PhysicalResourceId': event.get('PhysicalResourceId', context.log_stream_name),
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    })

    req = urllib.request.Request(
        event['ResponseURL'],
        data=response_body.encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    urllib.request.urlopen(req)

    return {'statusCode': 200 if status == 'SUCCESS' else 500}


def generate_certificate():
    """Generate or renew a Let's Encrypt certificate."""
    domain = os.environ['DOMAIN']
    zone_id = os.environ['ZONE_ID']
    secret_arn = os.environ['CERT_SECRET_ARN']

    print(f"Generating certificate for {domain}")

    try:
        # Import cryptography here to fail fast if unavailable
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec, rsa
        from cryptography.hazmat.backends import default_backend
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
    except ImportError as e:
        print(f"ERROR: cryptography library not available: {e}")
        return {'statusCode': 500, 'body': 'cryptography library not available'}

    secrets = boto3.client('secretsmanager')
    route53 = boto3.client('route53')

    # Get or create account key
    try:
        response = secrets.get_secret_value(SecretId=secret_arn)
        secret_data = json.loads(response['SecretString'])
        if 'account_key' in secret_data:
            account_key = serialization.load_pem_private_key(
                secret_data['account_key'].encode(),
                password=None,
                backend=default_backend()
            )
        else:
            account_key = None
    except:
        account_key = None
        secret_data = {}

    if account_key is None:
        print("Creating new ACME account key")
        account_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

    # Get ACME directory
    directory = json.loads(fetch_url(ACME_DIRECTORY))

    # Get nonce
    nonce = fetch_url(directory['newNonce'], method='HEAD', return_headers=True)['Replay-Nonce']

    # Create/retrieve account
    account_url, nonce = acme_register(directory['newAccount'], account_key, nonce)
    print(f"ACME account: {account_url}")

    # Generate certificate key
    cert_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Create CSR
    csr = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)])
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(domain)]),
        critical=False
    ).sign(cert_key, hashes.SHA256(), default_backend())

    csr_der = csr.public_bytes(serialization.Encoding.DER)
    csr_b64 = base64url_encode(csr_der)

    # Create order
    order_payload = {'identifiers': [{'type': 'dns', 'value': domain}]}
    order_response, nonce = acme_request(
        directory['newOrder'], account_key, account_url, nonce, order_payload
    )
    order = json.loads(order_response['body'])
    order_url = order_response['headers'].get('Location')
    print(f"Order created: {order_url}")

    # Get authorization
    auth_url = order['authorizations'][0]
    auth_response, nonce = acme_request(auth_url, account_key, account_url, nonce, None)
    auth = json.loads(auth_response['body'])

    # Find DNS-01 challenge
    challenge = None
    for c in auth['challenges']:
        if c['type'] == 'dns-01':
            challenge = c
            break

    if not challenge:
        raise Exception("No DNS-01 challenge found")

    # Compute challenge response
    thumbprint = jwk_thumbprint(account_key)
    key_auth = f"{challenge['token']}.{thumbprint}"
    dns_value = base64url_encode(hashlib.sha256(key_auth.encode()).digest())

    # Create DNS TXT record
    txt_name = f"_acme-challenge.{domain}"
    print(f"Creating TXT record: {txt_name} = {dns_value}")

    change_response = route53.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            'Changes': [{
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': txt_name,
                    'Type': 'TXT',
                    'TTL': 60,
                    'ResourceRecords': [{'Value': f'"{dns_value}"'}]
                }
            }]
        }
    )
    change_id = change_response['ChangeInfo']['Id']

    # Wait for DNS propagation
    print("Waiting for DNS propagation...")
    while True:
        change_status = route53.get_change(Id=change_id)
        if change_status['ChangeInfo']['Status'] == 'INSYNC':
            break
        time.sleep(5)

    # Extra wait for DNS propagation
    time.sleep(10)

    # Notify ACME to verify challenge
    print("Requesting challenge verification...")
    _, nonce = acme_request(challenge['url'], account_key, account_url, nonce, {})

    # Poll for authorization status
    for _ in range(30):
        auth_response, nonce = acme_request(auth_url, account_key, account_url, nonce, None)
        auth = json.loads(auth_response['body'])

        if auth['status'] == 'valid':
            print("Challenge validated!")
            break
        elif auth['status'] == 'invalid':
            raise Exception(f"Challenge failed: {auth}")

        time.sleep(2)
    else:
        raise Exception("Challenge validation timeout")

    # Finalize order
    print("Finalizing order...")
    _, nonce = acme_request(order['finalize'], account_key, account_url, nonce, {'csr': csr_b64})

    # Poll for certificate
    for _ in range(30):
        order_response, nonce = acme_request(order_url, account_key, account_url, nonce, None)
        order = json.loads(order_response['body'])

        if order['status'] == 'valid' and 'certificate' in order:
            break
        elif order['status'] == 'invalid':
            raise Exception(f"Order failed: {order}")

        time.sleep(2)
    else:
        raise Exception("Order finalization timeout")

    # Download certificate
    print("Downloading certificate...")
    cert_response, _ = acme_request(order['certificate'], account_key, account_url, nonce, None)
    cert_pem = cert_response['body']

    # Parse certificate chain
    certs = cert_pem.split('-----END CERTIFICATE-----')
    certificate = certs[0] + '-----END CERTIFICATE-----\n'
    chain = '-----END CERTIFICATE-----'.join(certs[1:]).strip()
    if chain:
        chain = chain + '\n'

    # Parse expiry
    cert_obj = x509.load_pem_x509_certificate(certificate.encode(), default_backend())
    expires = cert_obj.not_valid_after_utc.isoformat()

    # Cleanup DNS record
    print("Cleaning up TXT record...")
    try:
        route53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                'Changes': [{
                    'Action': 'DELETE',
                    'ResourceRecordSet': {
                        'Name': txt_name,
                        'Type': 'TXT',
                        'TTL': 60,
                        'ResourceRecords': [{'Value': f'"{dns_value}"'}]
                    }
                }]
            }
        )
    except Exception as e:
        print(f"Warning: failed to delete TXT record: {e}")

    # Store certificate in Secrets Manager
    private_key_pem = cert_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    account_key_pem = account_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    cert_data = {
        'certificate': certificate,
        'chain': chain,
        'private_key': private_key_pem,
        'domain': domain,
        'expires': expires,
        'account_key': account_key_pem
    }

    secrets.put_secret_value(SecretId=secret_arn, SecretString=json.dumps(cert_data))

    print(f"Certificate stored successfully! Expires: {expires}")
    return {'statusCode': 200, 'body': json.dumps({'message': 'Certificate generated', 'expires': expires})}


def fetch_url(url, method='GET', data=None, headers=None, return_headers=False):
    """Fetch a URL and return the response."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            if return_headers:
                return dict(response.headers)
            return response.read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise Exception(f"HTTP {e.code}: {body}")


def base64url_encode(data):
    """Base64url encode without padding."""
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def jwk_thumbprint(key):
    """Compute JWK thumbprint for an EC key."""
    from cryptography.hazmat.primitives.asymmetric import ec

    public_key = key.public_key()
    numbers = public_key.public_numbers()

    if isinstance(key, ec.EllipticCurvePrivateKey):
        # EC key
        x = numbers.x.to_bytes(32, 'big')
        y = numbers.y.to_bytes(32, 'big')
        jwk = {
            'crv': 'P-256',
            'kty': 'EC',
            'x': base64url_encode(x),
            'y': base64url_encode(y)
        }
    else:
        raise Exception("Unsupported key type")

    jwk_json = json.dumps(jwk, sort_keys=True, separators=(',', ':'))
    return base64url_encode(hashlib.sha256(jwk_json.encode()).digest())


def acme_register(url, key, nonce):
    """Register or retrieve existing ACME account."""
    payload = {'termsOfServiceAgreed': True}
    response, new_nonce = acme_request(url, key, None, nonce, payload)
    account_url = response['headers'].get('Location')
    return account_url, new_nonce


def acme_request(url, key, account_url, nonce, payload):
    """Make a signed ACME request."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes

    public_key = key.public_key()
    numbers = public_key.public_numbers()

    # Build JWK for header
    x = numbers.x.to_bytes(32, 'big')
    y = numbers.y.to_bytes(32, 'big')
    jwk = {
        'crv': 'P-256',
        'kty': 'EC',
        'x': base64url_encode(x),
        'y': base64url_encode(y)
    }

    # Build protected header
    protected = {
        'alg': 'ES256',
        'nonce': nonce,
        'url': url
    }

    if account_url:
        protected['kid'] = account_url
    else:
        protected['jwk'] = jwk

    protected_b64 = base64url_encode(json.dumps(protected))

    if payload is None:
        payload_b64 = ''
    else:
        payload_b64 = base64url_encode(json.dumps(payload))

    # Sign
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    signature = key.sign(signing_input, ec.ECDSA(hashes.SHA256()))

    # Convert DER signature to raw r||s format
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    r, s = decode_dss_signature(signature)
    signature_bytes = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')

    jws = {
        'protected': protected_b64,
        'payload': payload_b64,
        'signature': base64url_encode(signature_bytes)
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(jws).encode(),
        headers={'Content-Type': 'application/jose+json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            return {
                'body': response.read().decode(),
                'headers': dict(response.headers)
            }, response.headers.get('Replay-Nonce')
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # Return nonce even on error for retry
        new_nonce = e.headers.get('Replay-Nonce', nonce)
        raise Exception(f"ACME error {e.code}: {body}")
