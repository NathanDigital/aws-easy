# Dynamic DNS

Update a Route 53 DNS record automatically when your home IP address changes.

[![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=dynamic-dns&templateURL=https://raw.githubusercontent.com/NathanDigital/aws-easy/main/templates/dynamic-dns/template.yaml)

## What You Get

- **IAM User**: Limited permissions to update only your specific DNS record
- **Access Keys**: Credentials for your update script/device

## Prerequisites

- A domain hosted in Route 53
- Your Route 53 Hosted Zone ID (find it in the Route 53 console)

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `HostedZoneId` | Yes | Your Route 53 Hosted Zone ID (e.g., `Z1234567890ABC`) |
| `RecordName` | Yes | The DNS record to update (e.g., `home.example.com`) |

## Steps

1. Click the "Launch Stack" button above
2. Enter your Hosted Zone ID and record name
3. Click "Create stack"
4. Go to the "Outputs" tab and copy the Access Key ID and Secret

## Update Script

Run this script on your home server/router to update the DNS record:

```bash
#!/bin/bash
# Save as update-dns.sh

ACCESS_KEY="YOUR_ACCESS_KEY_ID"
SECRET_KEY="YOUR_SECRET_ACCESS_KEY"
HOSTED_ZONE_ID="YOUR_HOSTED_ZONE_ID"
RECORD_NAME="home.example.com"

# Get current public IP
IP=$(curl -s https://checkip.amazonaws.com)

# Update Route 53
AWS_ACCESS_KEY_ID=$ACCESS_KEY AWS_SECRET_ACCESS_KEY=$SECRET_KEY \
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "'"$RECORD_NAME"'",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'"$IP"'"}]
      }
    }]
  }'
```

Run via cron every 5 minutes:

```bash
*/5 * * * * /path/to/update-dns.sh
```

## Costs

- Route 53 Hosted Zone: $0.50/month
- DNS queries: $0.40 per million queries

## Cleanup

```bash
aws cloudformation delete-stack --stack-name dynamic-dns
```
