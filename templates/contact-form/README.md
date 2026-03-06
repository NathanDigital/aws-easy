# Contact Form

Add a contact form to your static website. Submissions are sent to your email via Amazon SES.

<a href="https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=https://aws-easy-templates.s3.ap-southeast-2.amazonaws.com/templates/contact-form/template.yaml&stackName=contact-form&capabilities=CAPABILITY_IAM" target="_blank"><img src="https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png" alt="Launch Stack"></a>

## What You Get

- **API endpoint**: HTTPS URL to receive form submissions
- **Email delivery**: Messages sent to your inbox via Amazon SES
- **Spam protection**: Hidden honeypot field catches bots
- **CORS enabled**: Works from any website

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `RecipientEmail` | Yes | Email address to receive form submissions |

## Setup

1. Click the "Launch Stack" button above
2. Enter your email address
3. Check "I acknowledge..." at the bottom
4. Click **Create stack**
5. Wait for status to show `CREATE_COMPLETE` (1-2 mins)
6. **Check your inbox** for a verification email from AWS and click the link
7. Click the **Outputs** tab for your endpoint URL and auth token

**Important:** Form submissions will fail until you verify your email address by clicking the link in step 6.

## Integration

### HTML Form

Add this form to your website:

```html
<form id="contact-form">
  <input type="email" name="email" placeholder="Your email" required>
  <!-- Honeypot field - leave hidden -->
  <input type="text" name="website" style="display:none" tabindex="-1" autocomplete="off">
  <textarea name="message" placeholder="Your message" required></textarea>
  <button type="submit">Send</button>
</form>
```

### JavaScript

Add this script, replacing the URL and token with values from your stack Outputs:

```javascript
document.getElementById('contact-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form));

  const res = await fetch('YOUR_FORM_URL', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer YOUR_TOKEN'
    },
    body: JSON.stringify(data)
  });

  const result = await res.json();
  if (res.ok) {
    alert('Message sent!');
    form.reset();
  } else {
    alert(result.error || 'Failed to send');
  }
});
```

### Honeypot Field

The hidden `website` field is a spam trap. Real users won't see or fill it, but bots often fill every field. If it contains a value, the submission is silently ignored.

**Don't remove this field** - it's your primary spam protection.

## Security Notes

The auth token is visible in your JavaScript, which means anyone can see it by viewing your page source. This is intentional and acceptable because:

- The token provides basic protection against casual abuse
- The honeypot field catches most automated spam
- SES has built-in rate limiting
- For higher security needs, you'd want server-side form handling anyway

If you experience abuse, you can:
1. Delete and recreate the stack (generates a new token)
2. Add rate limiting via AWS WAF (more complex)

## Costs

SES charges $0.10 per 1,000 emails sent. For a typical contact form:

- **10 submissions/month**: ~$0.00
- **1,000 submissions/month**: ~$0.10
- **Lambda & API Gateway**: Negligible (< $0.01/month)

**Total: Essentially free** for normal usage.

## Cleanup

To delete and stop charges:

1. Go to [CloudFormation Stacks](https://console.aws.amazon.com/cloudformation/home#/stacks)
2. Select your stack and click **Delete**

## Troubleshooting

**503 "Email not yet verified"**

You haven't clicked the verification link yet. Check your inbox (and spam folder) for an email from AWS with subject "Amazon Web Services - Email Address Verification Request".

**403 "Unauthorized"**

Your authorization header is incorrect. Make sure it's exactly `Authorization: Bearer YOUR_TOKEN` with a space after "Bearer".

**400 "Email and message required"**

The request body is missing the `email` or `message` field. Check that your form fields have the correct `name` attributes.

**No email received (but API returns success)**

- Check your spam folder
- Verify you're checking the correct email address
- Look at CloudWatch Logs for the Lambda function for any errors

**CORS errors in browser console**

Make sure you're using `POST` method and including both `Content-Type` and `Authorization` headers. The API handles CORS automatically for these.
