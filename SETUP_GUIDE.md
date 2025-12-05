# Setup Guide - Manuscript Processor

This guide will help you set up the Manuscript Processor application on your local machine.

## Prerequisites

### 1. Install Node.js
- Download and install Node.js (v16 or higher) from [nodejs.org](https://nodejs.org/)
- Verify installation:
  ```bash
  node --version
  npm --version
  ```

### 2. Install Python
The document converter requires Python 3.x.

#### Windows
- Download and install Python from [python.org](https://www.python.org/downloads/)
- **Important**: During installation, check "Add Python to PATH"
- Verify installation:
  ```bash
  python --version
  ```

#### Linux/Mac
- Python 3 is usually pre-installed
- Verify installation:
  ```bash
  python3 --version
  ```
- If not installed:
  ```bash
  # Ubuntu/Debian
  sudo apt-get update
  sudo apt-get install python3 python3-pip

  # macOS (using Homebrew)
  brew install python3
  ```

### 3. Install System Dependencies (for PDF processing)

#### Windows
1. Download Poppler for Windows from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)
2. Extract the ZIP file
3. Add the `bin` folder to your PATH environment variable
4. Verify installation:
   ```bash
   pdftohtml -v
   ```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils ghostscript

# CentOS/RHEL
sudo yum install poppler-utils ghostscript
```

#### macOS
```bash
brew install poppler ghostscript
```

### 4. Set up MongoDB
You can use either local MongoDB or MongoDB Atlas (cloud).

#### MongoDB Atlas (Recommended for beginners)
1. Create free account at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create a cluster (free tier available)
3. Get your connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)

#### Local MongoDB
- Download and install from [mongodb.com/download-center](https://www.mongodb.com/try/download/community)
- Start MongoDB service

## Installation Steps

### 1. Clone and Navigate to Project
```bash
git clone <repository-url>
cd demo-ui
```

### 2. Backend Setup

#### Install Dependencies
```bash
cd backend
npm install
```

#### Install Python Dependencies
```bash
# Windows
cd PDFtoXMLUsingExcel
python -m pip install -r requirements.txt
cd ..

# Linux/Mac
cd PDFtoXMLUsingExcel
python3 -m pip install -r requirements.txt
cd ..
```

#### Configure Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env file with your settings
```

**Required .env Configuration:**

```env
# Server
PORT=5000
NODE_ENV=development

# MongoDB - Use your MongoDB Atlas connection string or local MongoDB
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster0
# Or for local: MONGODB_URI=mongodb://localhost:27017/manuscript-processor

# JWT Secret - Change this to a random secure string
JWT_SECRET=your_super_secret_jwt_key_change_this_in_production

# Frontend URL
FRONTEND_URL=http://localhost:4201

# Email - Set to false to disable notifications
EMAIL_ENABLED=false

# Python Configuration (Optional - auto-detects if not set)
# Windows users: Leave commented to auto-detect 'python'
# Linux/Mac users: Leave commented to auto-detect 'python3'
# PDF_CONVERTER_PYTHON=python
# CONVERTER_PYTHON=python
```

#### Create Admin User
You need to manually create an admin user in MongoDB to get started.

**Option 1: Using MongoDB Compass (GUI)**
1. Download [MongoDB Compass](https://www.mongodb.com/products/compass)
2. Connect using your MongoDB URI
3. Create database: `manuscript-processor` or `test`
4. Create collection: `users`
5. Insert document:
   ```json
   {
     "username": "admin",
     "email": "admin@example.com",
     "password": "$2a$10$YourHashedPasswordHere",
     "role": "admin",
     "createdAt": {"$date": "2024-01-01T00:00:00.000Z"},
     "updatedAt": {"$date": "2024-01-01T00:00:00.000Z"}
   }
   ```

**Option 2: Generate Password Hash**
```bash
cd backend
node -e "const bcrypt = require('bcryptjs'); console.log(bcrypt.hashSync('your-password', 10));"
```
Copy the output and use it as the password value in MongoDB.

#### Start Backend Server
```bash
npm start
# Or for development with auto-reload:
npm run dev
```

The backend will start on http://localhost:5000

### 3. Frontend Setup

#### Install Dependencies
```bash
cd ../frontend
npm install
```

#### Configure Environment
```bash
cp .env.example .env
```

The default configuration should work:
```env
VITE_API_URL=http://localhost:5000/api
```

#### Start Frontend Server
```bash
npm run dev
```

The frontend will start on http://localhost:3000 or http://localhost:4200

## Verification

### 1. Check Backend Health
Open browser and navigate to:
```
http://localhost:5000/api/health
```
You should see: `{"status": "OK"}`

### 2. Test Login
1. Navigate to http://localhost:3000 (or frontend URL)
2. Enter admin credentials you created
3. You should be redirected to the dashboard

### 3. Test File Upload
1. Click "Upload Manuscript"
2. Select a small PDF file (1-2 pages for testing)
3. Check backend console for processing logs
4. File should process successfully if all dependencies are installed

## Troubleshooting

### Python Not Found Error
```
❌ Python executable not found!
```

**Solution:**
- Windows: Ensure Python is installed and in PATH. Try `python --version` in command prompt
- Linux/Mac: Try `python3 --version` in terminal
- If Python is installed but not detected, manually set in `.env`:
  ```env
  PDF_CONVERTER_PYTHON=python
  CONVERTER_PYTHON=python
  ```

### pdftohtml Command Not Found
```
Error: pdftohtml: command not found
```

**Solution:**
- Install Poppler (see Prerequisites section above)
- Restart terminal/command prompt after installation

### MongoDB Connection Failed
```
Error: connect ECONNREFUSED
```

**Solution:**
- Verify MongoDB is running (for local MongoDB)
- Check MongoDB URI in `.env` file
- For Atlas: Ensure IP address is whitelisted in Atlas dashboard
- Check username/password are correct (URL-encode special characters)

### Email Notification Errors
```
Error: Invalid login: 535-5.7.8 Username and Password not accepted
```

**Solution:**
- See detailed guide: `backend/EMAIL_SETUP_GUIDE.md`
- Quick fix: Set `EMAIL_ENABLED=false` in `.env` to disable email notifications
- For Gmail: You MUST use an App Password (not your regular password)
  - Enable 2FA on Google Account
  - Generate App Password at: Security > 2-Step Verification > App passwords
  - Use the 16-character App Password in `.env`

### Python Module Not Found Errors

#### PDF Converter Errors
```
ModuleNotFoundError: No module named 'openpyxl'
ModuleNotFoundError: No module named 'PyMuPDF'
ModuleNotFoundError: No module named 'camelot'
```

**Cause:** Python dependencies for the PDF converter are not installed

**Solution:**
```bash
# Navigate to the PDF converter directory
cd backend/PDFtoXMLUsingExcel

# Install dependencies
# Windows:
python -m pip install -r requirements.txt

# Linux/Mac:
python3 -m pip install -r requirements.txt

# Go back to backend directory
cd ..

# Restart the server
npm start
```

#### EPUB Converter Errors
```
ModuleNotFoundError: No module named 'ebooklib'
ModuleNotFoundError: No module named 'epub_to_structured_v2'
File not found: integrated_pipeline.py
```

**Cause:** RittDocConverter repository is not installed or missing dependencies

**Solution:**

**Step 1: Clone RittDocConverter (if not already done)**
```bash
cd backend
git clone https://github.com/Zentrovia/RittDocConverter.git
cd ..
```

**Step 2: Install EPUB converter dependencies**
```bash
cd backend/RittDocConverter

# If requirements.txt exists:
# Windows:
python -m pip install -r requirements.txt

# Linux/Mac:
python3 -m pip install -r requirements.txt

# If no requirements.txt exists, manually install:
# Windows:
python -m pip install ebooklib beautifulsoup4 lxml pillow

# Linux/Mac:
python3 -m pip install ebooklib beautifulsoup4 lxml pillow

cd ../..

# Restart the server
cd backend
npm start
```

#### General Solutions

**If you get permission errors:**
```bash
# Windows: Run Command Prompt as Administrator
python -m pip install -r requirements.txt

# Linux/Mac: Use --user flag
python3 -m pip install --user -r requirements.txt
```

**Using Virtual Environment (Recommended):**
```bash
# For PDF Converter:
# Windows
cd backend/PDFtoXMLUsingExcel
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ..\..

# Linux/Mac
cd backend/PDFtoXMLUsingExcel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ../..

# For EPUB Converter:
# Windows
cd backend/RittDocConverter
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt  # or manually install packages
deactivate
cd ..\..

# Linux/Mac
cd backend/RittDocConverter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or manually install packages
deactivate
cd ../..
```

### Port Already in Use
```
Error: listen EADDRINUSE: address already in use :::5000
```

**Solution:**
- Change PORT in backend/.env to different value (e.g., 5001)
- Or kill process using port 5000

### File Upload Fails Immediately
**Solution:**
- Check backend logs for specific error
- Verify `uploads/` directory exists and is writable
- Check file size (must be under 500MB)
- Verify file type (PDF or EPUB only)

## Production Deployment

For production deployment to AWS or other cloud platforms, see [backend/DEPLOYMENT.md](backend/DEPLOYMENT.md)

## Getting Help

If you encounter issues:
1. Check the backend console logs for detailed error messages
2. Verify all prerequisites are installed correctly
3. Ensure environment variables are configured properly
4. Create an issue on GitHub with error logs and system information
