# HTTPS Certificate

Auto-renewing Let's Encrypt TLS certificate with a secure API endpoint to download it. Perfect for IoT devices, home servers, or any service that needs valid HTTPS certificates.

<a href="https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://aws-easy-templates.s3.ap-southeast-2.amazonaws.com/templates/https-cert/template.yaml&stackName=https-cert&capabilities=CAPABILITY_IAM" target="_blank"><img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png" alt="Launch Stack"></a>

## What You Get

- **Let's Encrypt certificate**: Free, trusted TLS certificate for your domain
- **Auto-renewal**: Certificate renews automatically every 60 days
- **Secure API**: Download your certificate via HTTPS with bearer token auth
- **Secrets Manager storage**: Certificate and private key stored encrypted

## Prerequisites

- A domain you own (registered anywhere)
- A Route 53 hosted zone for your domain

### Setting up Route 53 (one-time)

If you haven't already:

1. Go to [Route 53 Hosted Zones](https://console.aws.amazon.com/route53/v2/hostedzones)
2. Click "Create hosted zone"
3. Enter your domain name (e.g., `example.com`)
4. Copy the 4 nameservers from the NS record
5. Update your domain's nameservers at your registrar
6. Wait for DNS propagation (can take up to 48 hours)

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `DomainName` | Yes | Domain for the certificate (e.g., `home.example.com`) |

The hosted zone is detected automatically. A secure random token is generated during deployment.

## Setup

1. Click the "Launch Stack" button above
2. Enter your domain name (e.g., `home.example.com`)
3. Check "I acknowledge..." at the bottom
4. Click **Create stack**
5. Wait for status to show `CREATE_COMPLETE` (may take a few minutes for initial certificate generation)
6. Click the **Outputs** tab
7. Copy the `CurlCommand` value

## Usage

### Download certificate

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://xxxxx.execute-api.us-east-1.amazonaws.com/cert
```

Response:
```json
{
  "certificate": "-----BEGIN CERTIFICATE-----\n...",
  "chain": "-----BEGIN CERTIFICATE-----\n...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "domain": "home.example.com",
  "expires": "2024-06-15T00:00:00+00:00"
}
```

### Save to files

```bash
curl -s -H "Authorization: Bearer YOUR_TOKEN" https://xxxxx.execute-api.us-east-1.amazonaws.com/cert | \
  jq -r '.certificate + .chain' > fullchain.pem

curl -s -H "Authorization: Bearer YOUR_TOKEN" https://xxxxx.execute-api.us-east-1.amazonaws.com/cert | \
  jq -r '.private_key' > privkey.pem
```

### Auto-update script

Create a script to periodically fetch and install the certificate:

```bash
#!/bin/bash
CERT_URL="https://xxxxx.execute-api.us-east-1.amazonaws.com/cert"
AUTH_HEADER="Bearer YOUR_TOKEN"

# Fetch certificate
CERT_JSON=$(curl -s -H "Authorization: $AUTH_HEADER" "$CERT_URL")

# Save files
echo "$CERT_JSON" | jq -r '.certificate + .chain' > /etc/ssl/fullchain.pem
echo "$CERT_JSON" | jq -r '.private_key' > /etc/ssl/privkey.pem

# Reload your service (example for nginx)
systemctl reload nginx
```

Add to crontab to run weekly:
```
0 3 * * 0 /path/to/update-cert.sh
```

### ESP32 / Arduino

```cpp
#include <HTTPClient.h>
#include <ArduinoJson.h>

void fetchCertificate() {
  HTTPClient http;
  http.begin("https://xxxxx.execute-api.us-east-1.amazonaws.com/cert");
  http.addHeader("Authorization", "Bearer YOUR_TOKEN");

  int httpCode = http.GET();
  if (httpCode == 200) {
    String payload = http.getString();
    JsonDocument doc;
    deserializeJson(doc, payload);

    const char* cert = doc["certificate"];
    const char* key = doc["private_key"];
    // Use cert and key for TLS server
  }
  http.end();
}
```

## Security

- **Bearer token auth**: Only requests with your secret token can download the certificate
- **HTTPS only**: All API requests are encrypted
- **Secrets Manager**: Certificate stored with AWS encryption at rest
- **Scoped permissions**: Lambda can only manage TXT records (for ACME challenge)

**Keep your token secret!** Anyone with the token can download your private key.

## How It Works

1. **Initial deployment**: Lambda generates a certificate using Let's Encrypt's ACME protocol
2. **DNS validation**: Creates a temporary `_acme-challenge.your-domain.com` TXT record
3. **Certificate issued**: Let's Encrypt verifies DNS and issues the certificate
4. **Storage**: Certificate and private key stored in Secrets Manager
5. **Auto-renewal**: EventBridge triggers renewal every 60 days
6. **API access**: Download via authenticated HTTPS endpoint

## Costs

Excluding free tier:

- **Lambda**: ~$0.01/month (runs twice per 60-day renewal cycle + API calls)
- **API Gateway**: ~$0.01/month
- **Secrets Manager**: $0.40/month per secret
- **Route 53**: $0.50/month per hosted zone (if not already using)

**Total: ~$0.50-1.00/month**

## Cleanup

To delete and stop charges:

1. Go to [CloudFormation Stacks](https://console.aws.amazon.com/cloudformation/home#/stacks)
2. Select your stack and click **Delete**

## Troubleshooting

**Certificate not generating**

Check CloudWatch Logs at `/aws/lambda/STACK_NAME-cert` for error details.

**403 Forbidden on API**

Your authorization header is incorrect. Make sure it's exactly `Bearer YOUR_TOKEN` with a space after Bearer.

**DNS validation failing**

- Ensure your domain's nameservers point to Route 53
- Check that the hosted zone exists and matches your domain
- Wait for DNS propagation if you recently changed nameservers

**Manual renewal**

To force a renewal, invoke the Lambda function directly:

```bash
aws lambda invoke --function-name STACK_NAME-cert /dev/null
```
