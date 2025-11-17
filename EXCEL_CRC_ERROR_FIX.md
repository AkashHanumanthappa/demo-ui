# Excel CRC-32 Error Fix

## Problem

The RittDocConverter pipeline is encountering a `BadZipFile: Bad CRC-32 for file 'xl/worksheets/sheet1.xml'` error when trying to load an existing Excel file.

### Error Details

```
zipfile.BadZipFile: Bad CRC-32 for file 'xl/worksheets/sheet1.xml'
```

This error occurs in `conversion_tracker.py` at line 248 in the `_save_to_excel` method when openpyxl tries to load a corrupted Excel file.

## Root Cause

The Excel file becomes corrupted during the conversion process or due to:
1. Incomplete writes to the Excel file
2. Process interruption during file writing
3. Concurrent access to the same Excel file
4. File system errors

## Solution

The fix needs to be applied in the **RittDocConverter** repository (not demo-ui). Here's what needs to be changed in `conversion_tracker.py`:

### Current Code (Problematic)

```python
def _save_to_excel(self):
    try:
        wb = openpyxl.load_workbook(self.excel_path)  # This line fails if file is corrupted
        # ... rest of the code
```

### Fixed Code

```python
import os
from zipfile import BadZipFile

def _save_to_excel(self):
    try:
        # Try to load existing workbook
        try:
            wb = openpyxl.load_workbook(self.excel_path)
        except (BadZipFile, Exception) as load_error:
            # If file is corrupted, delete it and create a new one
            self.logger.warning(f"Excel file corrupted ({load_error}), recreating: {self.excel_path}")
            if os.path.exists(self.excel_path):
                os.remove(self.excel_path)
            # Create new workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Conversion Tracker"
            # Add headers
            headers = ['Timestamp', 'Input File', 'Output Files', 'Status', 'Error Message']
            for col, header in enumerate(headers, start=1):
                ws.cell(row=1, column=col, value=header)

        # ... rest of your existing code to add data to workbook

    except Exception as e:
        self.logger.error(f"Failed to save to Excel: {e}")
        raise
```

## Implementation Steps

1. Navigate to the RittDocConverter repository
2. Open `conversion_tracker.py`
3. Locate the `_save_to_excel` method (around line 248)
4. Add the try-except block to handle `BadZipFile` exception
5. Add logic to recreate the Excel file when corrupted
6. Test the fix by:
   - Running a conversion
   - Manually corrupting the Excel file
   - Running another conversion to verify it recreates the file

## Alternative Solution (If the issue persists)

If the Excel file corruption continues, consider:

1. **Use file locking** to prevent concurrent access:
```python
import fcntl  # Unix/Linux
# or
import msvcrt  # Windows

# Lock file before writing
with open(self.excel_path, 'r+b') as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    # Write to Excel
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

2. **Write to temporary file first**, then rename:
```python
import tempfile
import shutil

# Write to temp file
temp_path = f"{self.excel_path}.tmp"
wb.save(temp_path)

# Replace original file atomically
shutil.move(temp_path, self.excel_path)
```

3. **Use a database instead of Excel** for tracking conversions (SQLite, PostgreSQL, etc.)

## Related Files

- `RittDocConverter/conversion_tracker.py` (line 248)
- This issue does NOT affect the demo-ui repository

## Testing

After applying the fix:

1. Run a normal conversion - should work
2. Manually corrupt the Excel file
3. Run another conversion - should recreate the file and work
4. Check logs for the warning message about file recreation
