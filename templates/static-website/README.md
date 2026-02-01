# Static Website Hosting

Host a static website (HTML, CSS, JavaScript) on AWS with HTTPS.

[![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://aws-easy-templates.s3.ap-southeast-2.amazonaws.com/templates/static-website/template.yaml&stackName=static-website)

## What You Get

- **S3 Bucket**: Stores your website files
- **CloudFront CDN**: Fast global delivery with HTTPS

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `DomainName` | No | Your custom domain (e.g., `example.com`). Leave blank to use the CloudFront URL. |

## Steps

1. Click the "Launch Stack" button above
2. Log into AWS if prompted
3. Optionally enter a custom domain, or leave blank
4. Click **Create stack**
5. Wait for status to show `CREATE_COMPLETE` (5-10 mins)
6. Click the **Outputs** tab
7. Copy the `WebsiteURL` and `BucketName`

## Upload Your Files

Once deployed, upload your website files:

1. Go to [S3 Console](https://console.aws.amazon.com/s3)
2. Find your bucket (check stack Outputs for the name)
3. Click "Upload" and add your files (must include `index.html`)

## Costs

A small personal website typically costs less than $1/month.

## Cleanup

To delete and stop charges:

```bash
aws s3 rm s3://YOUR-BUCKET-NAME --recursive
aws cloudformation delete-stack --stack-name static-website
```
