# Template Hosting (Internal)

This template creates the S3 bucket used to host aws-easy CloudFormation templates. It's project infrastructure, not intended for end users.

## Why this exists

CloudFormation's "Launch Stack" button requires templates to be hosted on S3. GitHub raw URLs don't work.

## What it creates

- **S3 bucket** (`aws-easy-templates`) - Public read access for CloudFormation
- **OIDC provider** - Allows GitHub Actions to authenticate without stored credentials
- **IAM role** - Scoped to this repo only, allows S3 sync

## Deployment

This only needs to be deployed once by the project maintainer:

```bash
aws cloudformation create-stack \
  --stack-name aws-easy-template-hosting \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

After deployment, note the `GitHubActionsRoleArn` output for use in the workflow.

## Syncing templates

Templates are synced to S3 via GitHub Actions on push to main. The workflow uses OIDC to assume the IAM role - no AWS credentials stored in GitHub.
