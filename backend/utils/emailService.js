const nodemailer = require('nodemailer');

/**
 * Email Service for sending conversion notifications
 */

// Create reusable transporter
const createTransporter = () => {
  // Check if email is enabled
  if (!process.env.EMAIL_ENABLED || process.env.EMAIL_ENABLED === 'false') {
    console.log('Email notifications are disabled');
    return null;
  }

  // Validate required email configuration
  if (!process.env.EMAIL_HOST || !process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
    console.warn('Email configuration incomplete. Email notifications will not be sent.');
    return null;
  }

  try {
    return nodemailer.createTransport({
      host: process.env.EMAIL_HOST,
      port: parseInt(process.env.EMAIL_PORT) || 587,
      secure: process.env.EMAIL_SECURE === 'true', // true for 465, false for other ports
      auth: {
        user: process.env.EMAIL_USER,
        pass: process.env.EMAIL_PASS,
      },
    });
  } catch (error) {
    console.error('Failed to create email transporter:', error);
    return null;
  }
};

/**
 * Generate HTML template for successful conversion
 */
const getSuccessEmailTemplate = (fileName, outputFiles, fileId) => {
  const downloadUrl = `${process.env.FRONTEND_URL || 'http://localhost:5173'}/manuscripts`;

  const outputFilesList = outputFiles
    .map(file => `<li>${file.fileName} (${(file.fileSize / 1024).toFixed(2)} KB)</li>`)
    .join('');

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          font-family: Arial, sans-serif;
          line-height: 1.6;
          color: #333;
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }
        .header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 30px;
          border-radius: 10px 10px 0 0;
          text-align: center;
        }
        .content {
          background: #f9f9f9;
          padding: 30px;
          border-radius: 0 0 10px 10px;
          border: 1px solid #e0e0e0;
          border-top: none;
        }
        .success-icon {
          font-size: 48px;
          margin-bottom: 10px;
        }
        .file-info {
          background: white;
          padding: 15px;
          border-radius: 8px;
          margin: 20px 0;
          border-left: 4px solid #10b981;
        }
        .output-files {
          background: white;
          padding: 15px;
          border-radius: 8px;
          margin: 20px 0;
        }
        .output-files ul {
          margin: 10px 0;
          padding-left: 20px;
        }
        .output-files li {
          margin: 8px 0;
          color: #555;
        }
        .button {
          display: inline-block;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 12px 30px;
          text-decoration: none;
          border-radius: 5px;
          margin: 20px 0;
          font-weight: bold;
        }
        .footer {
          text-align: center;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #e0e0e0;
          color: #777;
          font-size: 12px;
        }
      </style>
    </head>
    <body>
      <div class="header">
        <div class="success-icon">✅</div>
        <h1>Conversion Completed Successfully!</h1>
      </div>
      <div class="content">
        <p>Great news! Your document conversion has been completed successfully.</p>

        <div class="file-info">
          <h3 style="margin-top: 0; color: #10b981;">Original File</h3>
          <p style="margin: 5px 0;"><strong>${fileName}</strong></p>
        </div>

        <div class="output-files">
          <h3 style="margin-top: 0; color: #667eea;">Generated Files</h3>
          <p>The following files have been generated and are ready for download:</p>
          <ul>
            ${outputFilesList}
          </ul>
        </div>

        <div style="text-align: center;">
          <a href="${downloadUrl}" class="button">Download Your Files</a>
        </div>

        <p style="margin-top: 30px; color: #666; font-size: 14px;">
          <strong>Note:</strong> Your converted files are securely stored and can be accessed anytime from your dashboard.
        </p>
      </div>
      <div class="footer">
        <p>This is an automated notification from Document Conversion Service</p>
        <p>If you did not request this conversion, please contact support immediately.</p>
      </div>
    </body>
    </html>
  `;
};

/**
 * Generate HTML template for failed conversion
 */
const getFailureEmailTemplate = (fileName, errorMessage) => {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          font-family: Arial, sans-serif;
          line-height: 1.6;
          color: #333;
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }
        .header {
          background: linear-gradient(135deg, #f43f5e 0%, #dc2626 100%);
          color: white;
          padding: 30px;
          border-radius: 10px 10px 0 0;
          text-align: center;
        }
        .content {
          background: #f9f9f9;
          padding: 30px;
          border-radius: 0 0 10px 10px;
          border: 1px solid #e0e0e0;
          border-top: none;
        }
        .error-icon {
          font-size: 48px;
          margin-bottom: 10px;
        }
        .file-info {
          background: white;
          padding: 15px;
          border-radius: 8px;
          margin: 20px 0;
          border-left: 4px solid #f43f5e;
        }
        .error-details {
          background: #fff3f3;
          padding: 15px;
          border-radius: 8px;
          margin: 20px 0;
          border: 1px solid #fecaca;
        }
        .button {
          display: inline-block;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 12px 30px;
          text-decoration: none;
          border-radius: 5px;
          margin: 20px 0;
          font-weight: bold;
        }
        .footer {
          text-align: center;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #e0e0e0;
          color: #777;
          font-size: 12px;
        }
        .support-info {
          background: #f0f9ff;
          padding: 15px;
          border-radius: 8px;
          margin: 20px 0;
          border-left: 4px solid #3b82f6;
        }
      </style>
    </head>
    <body>
      <div class="header">
        <div class="error-icon">❌</div>
        <h1>Conversion Failed</h1>
      </div>
      <div class="content">
        <p>We're sorry, but your document conversion encountered an error and could not be completed.</p>

        <div class="file-info">
          <h3 style="margin-top: 0; color: #f43f5e;">File</h3>
          <p style="margin: 5px 0;"><strong>${fileName}</strong></p>
        </div>

        <div class="error-details">
          <h3 style="margin-top: 0; color: #dc2626;">Error Details</h3>
          <p style="margin: 5px 0; font-family: monospace; font-size: 13px; color: #991b1b;">
            ${errorMessage || 'An unknown error occurred during conversion'}
          </p>
        </div>

        <div class="support-info">
          <h3 style="margin-top: 0; color: #3b82f6;">What can you do?</h3>
          <ul style="margin: 10px 0; padding-left: 20px;">
            <li>Verify your file is not corrupted</li>
            <li>Ensure the file format is supported (PDF or EPUB)</li>
            <li>Try uploading the file again</li>
            <li>Contact support if the problem persists</li>
          </ul>
        </div>

        <div style="text-align: center;">
          <a href="${process.env.FRONTEND_URL || 'http://localhost:5173'}/manuscripts" class="button">Try Again</a>
        </div>
      </div>
      <div class="footer">
        <p>This is an automated notification from Document Conversion Service</p>
        <p>Need help? Contact our support team</p>
      </div>
    </body>
    </html>
  `;
};

/**
 * Send conversion success notification
 */
const sendConversionSuccessEmail = async (userEmail, fileName, outputFiles, fileId) => {
  const transporter = createTransporter();

  if (!transporter) {
    console.log('Email transporter not available. Skipping email notification.');
    return { success: false, message: 'Email service not configured' };
  }

  try {
    const mailOptions = {
      from: `"Document Conversion Service" <${process.env.EMAIL_USER}>`,
      to: userEmail,
      subject: `✅ Conversion Completed - ${fileName}`,
      html: getSuccessEmailTemplate(fileName, outputFiles, fileId),
      text: `Your document "${fileName}" has been successfully converted! ${outputFiles.length} file(s) are ready for download. Visit your dashboard to access them.`,
    };

    const info = await transporter.sendMail(mailOptions);
    console.log(`Success email sent to ${userEmail}: ${info.messageId}`);

    return {
      success: true,
      messageId: info.messageId,
      message: 'Success email sent successfully'
    };
  } catch (error) {
    console.error('Failed to send success email:', error);
    return {
      success: false,
      error: error.message,
      message: 'Failed to send success email'
    };
  }
};

/**
 * Send conversion failure notification
 */
const sendConversionFailureEmail = async (userEmail, fileName, errorMessage) => {
  const transporter = createTransporter();

  if (!transporter) {
    console.log('Email transporter not available. Skipping email notification.');
    return { success: false, message: 'Email service not configured' };
  }

  try {
    const mailOptions = {
      from: `"Document Conversion Service" <${process.env.EMAIL_USER}>`,
      to: userEmail,
      subject: `❌ Conversion Failed - ${fileName}`,
      html: getFailureEmailTemplate(fileName, errorMessage),
      text: `Your document "${fileName}" conversion failed. Error: ${errorMessage || 'Unknown error'}. Please try again or contact support.`,
    };

    const info = await transporter.sendMail(mailOptions);
    console.log(`Failure email sent to ${userEmail}: ${info.messageId}`);

    return {
      success: true,
      messageId: info.messageId,
      message: 'Failure email sent successfully'
    };
  } catch (error) {
    console.error('Failed to send failure email:', error);
    return {
      success: false,
      error: error.message,
      message: 'Failed to send failure email'
    };
  }
};

module.exports = {
  sendConversionSuccessEmail,
  sendConversionFailureEmail,
};
