# Dynamic DNS

Update a Route 53 DNS record automatically when your home IP address changes.

<a href="https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://aws-easy-templates.s3.ap-southeast-2.amazonaws.com/templates/dynamic-dns/template.yaml&stackName=dynamic-dns&capabilities=CAPABILITY_IAM" target="_blank"><img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png" alt="Launch Stack"></a>

## What You Get

- **Lambda function**: Detects your IP and updates Route 53
- **API Gateway**: HTTPS endpoint you can curl from anywhere
- **Bearer token auth**: Secure header-based authentication

## Prerequisites

- A domain you own (registered anywhere - Route 53, GoDaddy, Namecheap, etc.)
- A Route 53 hosted zone for your domain

### Setting up Route 53 (one-time)

If you haven't already:

1. Go to [Route 53 Hosted Zones](https://console.aws.amazon.com/route53/v2/hostedzones)
2. Click "Create hosted zone"
3. Enter your domain name (e.g., `example.com`)
4. Copy the 4 nameservers from the NS record (e.g., `ns-123.awsdns-45.com`)
5. Update your domain's nameservers at your registrar to use these
6. Wait for DNS propagation (can take up to 48 hours, usually faster)

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `RecordName` | Yes | The full DNS record to update (e.g., `home.example.com`) |

The hosted zone is detected automatically from your domain. A secure random token is generated during deployment.

## Setup

1. Click the "Launch Stack" button above
2. Enter your DNS record (e.g., `home.example.com`)
3. Check "I acknowledge..." at the bottom
4. Click **Create stack**
5. Wait for status to show `CREATE_COMPLETE` (2-3 mins)
6. Click the **Outputs** tab
7. Copy the `CurlCommand` or `CronCommand` value

## Usage

### One-time update

Use the `CurlCommand` from the Outputs tab:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://xxxxx.execute-api.us-east-1.amazonaws.com/update
```

Response:
```json
{"message": "DNS updated", "record": "home.example.com", "ip": "203.0.113.42"}
```

### Automatic updates (Linux/Mac)

Add the cron line from the Outputs to your crontab:

```bash
crontab -e
```

Paste the `CronCommand` value:
```
*/5 * * * * curl -s -H "Authorization: Bearer YOUR_TOKEN" https://xxxxx.execute-api.us-east-1.amazonaws.com/update
```

### From a router (OpenWrt/GL.iNet)

SSH into your router and add the cron job:

```bash
crontab -e
# Add the CronCommand from your stack Outputs
```

## Security

- **Header-based auth**: Token is sent in the Authorization header, not in the URL
- **HTTPS only**: All requests are encrypted
- **Token not logged**: Unlike URL tokens, header tokens don't appear in access logs

**Keep your token secret!** Anyone with the token can update your DNS record.

## Costs

With 5-minute updates (8,640 requests/month), excluding free tier:

- **Lambda**: ~$0.01/month
- **API Gateway**: ~$0.01/month
- **Route 53**: $0.50/month per hosted zone

**Total: ~$0.50/month**

## Cleanup

```bash
aws cloudformation delete-stack --stack-name dynamic-dns
```

## Troubleshooting

**403 Forbidden**

Your authorization header is incorrect. Make sure it's exactly `Authorization: Bearer YOUR_TOKEN` with a space after Bearer.

**DNS not updating**

Check CloudWatch Logs for the Lambda function to see error details.
