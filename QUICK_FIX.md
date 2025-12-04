# Quick Fix Guide - Current Errors

This guide addresses the errors you're currently experiencing with PDF and EPUB conversions.

## Error 1: ModuleNotFoundError (PDF Converter)

### Common errors:
```
ModuleNotFoundError: No module named 'openpyxl'
ModuleNotFoundError: No module named 'defusedxml.ElementTree'
ModuleNotFoundError: No module named 'PyMuPDF'
```

### What's happening:
The PDF converter Python script requires several libraries that aren't installed in your Python environment.

### Quick Fix:

**Windows:**
```bash
cd backend\PDFtoXMLUsingExcel

# If using virtual environment (venv312, venv, etc.):
venv312\Scripts\activate
# OR
venv\Scripts\activate

# Install/reinstall all dependencies
python -m pip install -r requirements.txt

# Deactivate venv (if activated)
deactivate

cd ..\..
```

**Linux/Mac:**
```bash
cd backend/PDFtoXMLUsingExcel

# If using virtual environment:
source venv/bin/activate

# Install/reinstall all dependencies
python3 -m pip install -r requirements.txt

# Deactivate venv (if activated)
deactivate

cd ../..
```

### What this installs:
- openpyxl (Excel file support)
- defusedxml (Secure XML parsing - required by openpyxl)
- PyMuPDF (PDF parsing)
- camelot-py (Table extraction)
- pandas, numpy (Data processing)
- And other required dependencies

**Important:** If you see `defusedxml` errors, the requirements.txt has been updated to include it explicitly. Just reinstall dependencies.

---

## Error 2: ModuleNotFoundError: No module named 'ebooklib' (EPUB Converter)

### What's happening:
The EPUB converter (RittDocConverter) is either:
1. Not installed (directory is empty)
2. Missing Python dependencies

### Quick Fix:

**Step 1: Clone RittDocConverter Repository**

```bash
cd backend

# Clone the RittDocConverter repository
git clone https://github.com/Zentrovia/RittDocConverter.git

cd ..
```

**Step 2: Install EPUB Converter Dependencies**

If the RittDocConverter repository has a `requirements.txt` file:

**Windows:**
```bash
cd backend\RittDocConverter
python -m pip install -r requirements.txt
cd ..\..
```

**Linux/Mac:**
```bash
cd backend/RittDocConverter
python3 -m pip install -r requirements.txt
cd ../..
```

**If no requirements.txt exists, manually install:**

```bash
# Windows:
python -m pip install ebooklib beautifulsoup4 lxml pillow

# Linux/Mac:
python3 -m pip install ebooklib beautifulsoup4 lxml pillow
```

### What this installs:
- ebooklib (EPUB parsing)
- beautifulsoup4 (HTML/XML parsing)
- lxml (XML processing)
- pillow (Image processing)

---

## Error 3: Invalid login: 535-5.7.8 Username and Password not accepted (Email)

### What's happening:
Gmail requires **App Passwords** for SMTP authentication. Your regular Gmail password will NOT work.

### Quick Fix Option 1: Disable Email (Fastest)

Edit `backend/.env` file:
```env
EMAIL_ENABLED=false
```

Then restart your backend server. The application will work normally without sending emails.

### Quick Fix Option 2: Set Up Gmail App Password (Recommended)

1. **Enable 2-Factor Authentication:**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Step Verification if not already enabled

2. **Generate App Password:**
   - Still in Security settings
   - Click on "2-Step Verification"
   - Scroll down to "App passwords"
   - Select "Mail" and "Other (Custom name)"
   - Name it "Document Conversion Service"
   - Click "Generate"
   - Copy the 16-character password (looks like: `abcd efgh ijkl mnop`)

3. **Update your `.env` file:**
   ```env
   EMAIL_ENABLED=true
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_SECURE=false
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASS=abcdefghijklmnop  # Paste App Password here (remove spaces)
   ```

4. **Restart backend server:**
   ```bash
   cd backend
   npm start
   ```

### For detailed email setup instructions:
See: `backend/EMAIL_SETUP_GUIDE.md`

---

## Summary of Required Actions

To get your application working properly:

### 1. ✅ **Install PDF Converter Dependencies** (Required for PDF conversion)

```bash
cd backend/PDFtoXMLUsingExcel

# If you have a virtual environment (venv312, venv), activate it first:
# Windows:
venv312\Scripts\activate  # or venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# Install dependencies:
python -m pip install -r requirements.txt  # Windows
# OR
python3 -m pip install -r requirements.txt  # Linux/Mac

# Deactivate venv if you activated it:
# deactivate

cd ../..
```

### 2. ✅ **Install EPUB Converter** (Required for EPUB conversion)

**Clone the repository:**
```bash
cd backend
git clone https://github.com/Zentrovia/RittDocConverter.git
cd ..
```

**Install dependencies:**
```bash
cd backend/RittDocConverter
# If requirements.txt exists:
python -m pip install -r requirements.txt  # Windows
# OR
python3 -m pip install -r requirements.txt  # Linux/Mac

# If no requirements.txt, manually install:
python -m pip install ebooklib beautifulsoup4 lxml pillow  # Windows
# OR
python3 -m pip install ebooklib beautifulsoup4 lxml pillow  # Linux/Mac
cd ../..
```

### 3. ✅ **Fix Email Configuration** (Choose one)

- **Option A (Quick):** Set `EMAIL_ENABLED=false` in `backend/.env`
- **Option B (Full setup):** Generate Gmail App Password and configure `.env`

### 4. ✅ **Restart the server**

```bash
cd backend
npm start
```

---

## Expected Outcome

After completing these steps:

✅ PDF conversion will work without `ModuleNotFoundError: No module named 'openpyxl'`
✅ EPUB conversion will work without `ModuleNotFoundError: No module named 'ebooklib'`
✅ Both PDF and EPUB files will process successfully
✅ Email notifications will either be disabled or working with proper authentication
✅ Users will receive email notifications (if enabled)
✅ No more "Invalid login" errors
✅ No more Windows Unicode encoding errors (UnicodeEncodeError)

---

## Windows-Specific Issue: Unicode Encoding Error (FIXED)

If you saw this error:
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'
```

**Good news:** This has been fixed in the code! The UTF-8 encoding is now automatically set for all Python processes.

**Note:** Even if you see this error, the conversion actually completes successfully. Check your files - they should be available for download despite the console error.

For more details, see: `WINDOWS_UNICODE_FIX.md`

---

## Still Having Issues?

### Check Python Installation:
```bash
# Windows:
python --version
python -m pip --version

# Linux/Mac:
python3 --version
python3 -m pip --version
```

### Check Node.js Server Logs:
Look for any errors when the server starts or when processing files.

### Verify Environment Variables:
Make sure your `backend/.env` file exists and has all required settings from `backend/.env.example`

---

## Additional Resources

- Complete Setup Guide: `SETUP_GUIDE.md`
- Email Configuration Guide: `backend/EMAIL_SETUP_GUIDE.md`
- Backend README: `backend/README.md`
- PDF Converter Dependencies: `backend/PDFtoXMLUsingExcel/requirements.txt`
