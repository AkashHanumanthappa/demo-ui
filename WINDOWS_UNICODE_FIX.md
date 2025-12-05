# Windows Console Encoding Fix for RittDocConverter

## Issue

When running EPUB conversions on Windows, you may encounter this error:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 0: character maps to <undefined>
```

**What's happening:**
- The conversion actually **completes successfully**
- The error occurs when trying to print Unicode characters (✓) to Windows Command Prompt
- Windows Command Prompt uses cp1252 encoding by default, which doesn't support Unicode characters

## Solution Options

### Option 1: Fix the RittDocConverter Code (Recommended)

Edit `backend/RittDocConverter/pipeline_controller.py`:

**Find line 39:**
```python
print(f"\u2713 Step completed: {step_name}")
```

**Replace with:**
```python
# Use ASCII-compatible character for Windows compatibility
checkmark = "✓" if sys.platform != "win32" else "[OK]"
print(f"{checkmark} Step completed: {step_name}")
```

**Also add this import at the top of the file:**
```python
import sys
```

### Option 2: Set UTF-8 Encoding for Python (Quick Fix)

Before running the backend server, set this environment variable:

**Windows Command Prompt:**
```cmd
set PYTHONIOENCODING=utf-8
cd backend
npm start
```

**Windows PowerShell:**
```powershell
$env:PYTHONIOENCODING="utf-8"
cd backend
npm start
```

**Permanent Fix (Add to backend/.env):**
```env
# Add this to your .env file
PYTHONIOENCODING=utf-8
```

Then update `backend/server.js` or wherever Node.js spawns Python processes to set this environment variable.

### Option 3: Modify the Node.js Python Spawn Process

Edit `backend/utils/docConverter.js` to set UTF-8 encoding:

**Find where Python process is spawned (around line 100-150):**
```javascript
const pythonProcess = spawn(pythonPath, args, {
  cwd: workingDir,
  env: process.env
});
```

**Replace with:**
```javascript
const pythonProcess = spawn(pythonPath, args, {
  cwd: workingDir,
  env: {
    ...process.env,
    PYTHONIOENCODING: 'utf-8'  // Add this line
  }
});
```

## Verification

After applying any of the fixes above:

1. Restart your backend server
2. Upload an EPUB file
3. Check the logs - you should see:
   - `[OK] Step completed: ePub to Structured XML Conversion` (Option 1)
   - `✓ Step completed: ePub to Structured XML Conversion` (Option 2 or 3)
4. No UnicodeEncodeError

## Important Note

**Even with this error, your EPUB conversion is successful!**

Check the database - you'll see the converted files are available for download. The error only affects the console output, not the actual conversion process.

## Quick Test

To verify the conversion worked despite the error:

1. Go to your frontend application
2. Check the files list - you should see the EPUB file with status "completed" or "failed"
3. If "completed", the download links should work
4. Check `backend/temp/[file-id]/output/` for the generated files (if temp directory still exists)

## Alternative: Ignore the Error

If you don't want to modify the RittDocConverter code, you can simply ignore this error:

- The conversion completes successfully
- Files are uploaded to GridFS
- Downloads work correctly
- The error is cosmetic (console output only)

## Related Issues

This is a known Windows issue with Python console encoding. See:
- https://github.com/python/cpython/issues/73545
- https://stackoverflow.com/questions/5419/python-unicode-and-the-windows-console

## Summary

**Quick Fix (Easiest):**
```cmd
set PYTHONIOENCODING=utf-8
cd backend
npm start
```

**Permanent Fix (Best):**
Edit `backend/utils/docConverter.js` to add `PYTHONIOENCODING: 'utf-8'` to the Python process environment.
