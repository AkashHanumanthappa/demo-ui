# Deployment Guide

## Environment Configuration

This application uses environment variables for configuration. The converter paths have been configured to work seamlessly across different environments (local development and AWS deployment).

### Setting Up Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the variables in `.env` according to your environment.

## Python Converter Setup

The application uses two Python-based converters:
- **PDFtoXMLUsingExcel**: Converts PDF files to XML
- **RittDocConverter**: Converts EPUB files to RittDoc format

### Local Development (Windows)

If you're using virtual environments on Windows:

```env
PDF_CONVERTER_DIR=./PDFtoXMLUsingExcel
PDF_CONVERTER_PYTHON=./PDFtoXMLUsingExcel/venv/Scripts/python.exe
PDF_CONVERTER_SCRIPT=pdf_to_unified_xml.py

CONVERTER_PYTHON=./RittDocConverter/venv/Scripts/python.exe
CONVERTER_SCRIPT_PATH=./RittDocConverter/integrated_pipeline.py
```

### Local Development (Linux/Mac)

```env
PDF_CONVERTER_DIR=./PDFtoXMLUsingExcel
PDF_CONVERTER_PYTHON=python3
PDF_CONVERTER_SCRIPT=pdf_to_unified_xml.py

CONVERTER_PYTHON=python3
CONVERTER_SCRIPT_PATH=./RittDocConverter/integrated_pipeline.py
```

### AWS Deployment

For AWS (EC2, Elastic Beanstalk, etc.):

```env
PDF_CONVERTER_DIR=./PDFtoXMLUsingExcel
PDF_CONVERTER_PYTHON=python3
PDF_CONVERTER_SCRIPT=pdf_to_unified_xml.py

CONVERTER_PYTHON=python3
CONVERTER_SCRIPT_PATH=./RittDocConverter/integrated_pipeline.py
```

## AWS Setup Instructions

### 1. Install Python Dependencies

SSH into your AWS instance and navigate to the backend directory:

```bash
cd /path/to/backend

# Install Python 3 if not already installed
sudo yum install python3 -y  # For Amazon Linux
# or
sudo apt-get install python3 -y  # For Ubuntu

# Install pip
sudo yum install python3-pip -y
# or
sudo apt-get install python3-pip -y
```

### 2. Set Up Python Virtual Environments (Optional but Recommended)

```bash
# For PDFtoXMLUsingExcel
cd PDFtoXMLUsingExcel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# For RittDocConverter
cd ../RittDocConverter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

If using venvs on AWS, update your `.env`:
```env
PDF_CONVERTER_PYTHON=./PDFtoXMLUsingExcel/venv/bin/python3
CONVERTER_PYTHON=./RittDocConverter/venv/bin/python3
```

### 3. Install System-Level Python Packages (Alternative)

If you prefer system-level installation:

```bash
# Install dependencies for PDFtoXMLUsingExcel
cd PDFtoXMLUsingExcel
sudo pip3 install -r requirements.txt

# Install dependencies for RittDocConverter
cd ../RittDocConverter
sudo pip3 install -r requirements.txt
```

Keep `.env` as:
```env
PDF_CONVERTER_PYTHON=python3
CONVERTER_PYTHON=python3
```

### 4. Set Environment Variables on AWS

#### For EC2 / Manual Deployment:
Create a `.env` file in the backend directory with production values.

#### For Elastic Beanstalk:
Set environment variables in the EB console or use `.ebextensions`:

```yaml
# .ebextensions/environment.config
option_settings:
  aws:elasticbeanstalk:application:environment:
    PDF_CONVERTER_DIR: "./PDFtoXMLUsingExcel"
    PDF_CONVERTER_PYTHON: "python3"
    PDF_CONVERTER_SCRIPT: "pdf_to_unified_xml.py"
    CONVERTER_PYTHON: "python3"
    CONVERTER_SCRIPT_PATH: "./RittDocConverter/integrated_pipeline.py"
```

#### For ECS / Docker:
Include environment variables in your task definition or docker-compose file.

### 5. File Permissions

Ensure the converter directories have proper permissions:

```bash
chmod -R 755 PDFtoXMLUsingExcel
chmod -R 755 RittDocConverter
```

## Testing the Setup

Test if the converters are working:

```bash
# Test PDF converter
cd backend/PDFtoXMLUsingExcel
python3 pdf_to_unified_xml.py --help

# Test EPUB converter
cd backend/RittDocConverter
python3 integrated_pipeline.py --help
```

## Troubleshooting

### Python not found
- Ensure `python3` is installed and in PATH
- Try using full path: `/usr/bin/python3`

### Module not found errors
- Install missing Python packages
- Check if virtual environment is properly set up

### Permission denied
- Check file permissions: `chmod +x script.py`
- Ensure the Node.js process has read/execute permissions

### Script not found
- Verify the script exists at the specified path
- Check that relative paths are correct from the backend directory

## Security Notes

- Never commit `.env` file to version control
- Use strong, unique values for `JWT_SECRET` in production
- Rotate MongoDB credentials regularly
- Use AWS Secrets Manager or Parameter Store for sensitive data in production
