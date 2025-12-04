# Email Configuration Setup Guide

## Overview
This guide will help you configure email notifications for the document conversion service. The application sends email notifications when file conversions succeed or fail.

## Common Issue: Gmail Authentication Error

### Error Message
```
Error: Invalid login: 535-5.7.8 Username and Password not accepted
```

### Cause
Gmail requires **App Passwords** when using SMTP authentication, especially if you have 2-Factor Authentication (2FA) enabled. Regular Gmail passwords will not work.

## Solution: Setting Up Gmail SMTP with App Password

### Step 1: Enable 2-Factor Authentication (if not already enabled)

1. Go to your [Google Account](https://myaccount.google.com/)
2. Navigate to **Security**
3. Under "Signing in to Google," select **2-Step Verification**
4. Follow the prompts to enable 2FA

### Step 2: Generate an App Password

1. Go to your [Google Account](https://myaccount.google.com/)
2. Navigate to **Security**
3. Under "Signing in to Google," select **2-Step Verification**
4. Scroll down and select **App passwords**
5. In the "Select app" dropdown, choose **Mail**
6. In the "Select device" dropdown, choose **Other (Custom name)**
7. Enter a name like "Document Conversion Service"
8. Click **Generate**
9. Google will display a 16-character password (e.g., `abcd efgh ijkl mnop`)
10. **Copy this password** - you'll need it for your .env file

### Step 3: Configure Your .env File

Create or update your `.env` file in the `backend` directory:

```env
# Email Configuration
EMAIL_ENABLED=true

# Gmail SMTP Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_SECURE=false
EMAIL_USER=your-email@gmail.com
EMAIL_PASS=abcdefghijklmnop  # Your 16-character App Password (remove spaces)
```

**Important Notes:**
- Remove spaces from the App Password (use `abcdefghijklmnop`, not `abcd efgh ijkl mnop`)
- Keep `EMAIL_SECURE=false` when using port 587
- Use `EMAIL_SECURE=true` if using port 465
- Never commit your `.env` file to version control

### Step 4: Restart Your Server

After updating the `.env` file, restart your Node.js server:

```bash
cd backend
npm start
```

## Alternative Email Providers

### SendGrid

```env
EMAIL_ENABLED=true
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_SECURE=false
EMAIL_USER=apikey
EMAIL_PASS=your-sendgrid-api-key
```

### Mailgun

```env
EMAIL_ENABLED=true
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_SECURE=false
EMAIL_USER=your-mailgun-smtp-username
EMAIL_PASS=your-mailgun-smtp-password
```

### Microsoft Office 365

```env
EMAIL_ENABLED=true
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_SECURE=true
EMAIL_USER=your-email@outlook.com
EMAIL_PASS=your-password
```

## Disabling Email Notifications

If you want to disable email notifications temporarily:

```env
EMAIL_ENABLED=false
```

The application will continue to work normally, but no emails will be sent.

## Testing Email Configuration

After configuring your email settings:

1. Upload a file for conversion
2. Check the server logs for email status:
   - Success: `Success email sent to user@example.com`
   - Failure: `Failed to send success email to user@example.com: [error details]`

## Troubleshooting

### Issue: "Email transporter not available"
**Solution:** Check that all required environment variables are set:
- `EMAIL_ENABLED=true`
- `EMAIL_HOST` is set
- `EMAIL_USER` is set
- `EMAIL_PASS` is set

### Issue: "Connection timeout"
**Solution:**
- Verify your internet connection
- Check if your firewall is blocking SMTP ports (587 or 465)
- Ensure EMAIL_HOST is correct

### Issue: "Self-signed certificate error"
**Solution:** For development only, you can disable SSL verification (not recommended for production):

```javascript
// In emailService.js createTransporter()
return nodemailer.createTransport({
  host: process.env.EMAIL_HOST,
  port: parseInt(process.env.EMAIL_PORT) || 587,
  secure: process.env.EMAIL_SECURE === 'true',
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS,
  },
  tls: {
    rejectUnauthorized: false  // Add this for development only
  }
});
```

### Issue: "Username and Password not accepted" (Gmail)
**Solution:**
- Make sure you're using an App Password, not your regular Gmail password
- Verify 2FA is enabled on your Google Account
- Check that you've copied the App Password correctly (no spaces)
- Try generating a new App Password if the old one doesn't work

## Security Best Practices

1. **Never commit `.env` files** to version control
2. Use App Passwords or API keys instead of actual passwords
3. Rotate your App Passwords periodically
4. Use environment-specific configurations (dev, staging, production)
5. Restrict SMTP credentials to only the services that need them
6. Monitor email logs for suspicious activity

## Additional Resources

- [Gmail App Passwords Guide](https://support.google.com/accounts/answer/185833)
- [Nodemailer Documentation](https://nodemailer.com/about/)
- [SMTP Port Reference](https://www.mailgun.com/blog/email/which-smtp-port-understanding-ports-25-465-587/)

## Support

If you continue to experience issues after following this guide:

1. Check the server logs for detailed error messages
2. Verify all environment variables are correctly set
3. Test your SMTP credentials with a tool like [smtp-test](https://www.npmjs.com/package/smtp-test)
4. Contact your email provider's support for authentication issues
