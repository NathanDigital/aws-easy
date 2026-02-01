# aws-easy

Simple CloudFormation templates and guides for common AWS tasks. No AWS expertise required.

## What is this?

AWS is powerful but complex. This project provides copy-paste CloudFormation templates with plain-English documentation for everyday tasks.

## Templates

### Static Website

Host a static website on S3 with CloudFront CDN.

[![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://aws-easy-templates.s3.ap-southeast-2.amazonaws.com/templates/static-website/template.yaml&stackName=static-website)

[Read the guide →](templates/static-website/)

---

### Dynamic DNS

Update Route 53 DNS records automatically from your home network.

[![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://aws-easy-templates.s3.ap-southeast-2.amazonaws.com/templates/dynamic-dns/template.yaml&stackName=dynamic-dns&capabilities=CAPABILITY_IAM)

[Read the guide →](templates/dynamic-dns/)

## Contributing

Contributions welcome! Please:

- Keep templates simple and well-documented
- Write READMEs that assume no AWS knowledge
- Test templates before submitting

## License

MIT
