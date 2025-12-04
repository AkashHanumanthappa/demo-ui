# Quick Start Guide - Metadata Integration

## What's New?

You can now automatically populate the BookInfo section of your Book.XML files by simply providing a metadata file (CSV or Excel format) in the same directory as your PDF.

## How to Use It

### Step 1: Create a Metadata File

Create a file named **`metadata.csv`** in the same directory as your PDF:

```csv
Field,Value
ISBN,978-1-234-56789-0
Title,My Book Title
Subtitle,A Comprehensive Guide
Author,John Doe
Author,Jane Smith
Publisher,My Publishing House
PublicationDate,2024
Edition,2nd Edition
CopyrightYear,2024
CopyrightHolder,My Publishing House
```

**Tip:** You can also use Excel files (`.xlsx` or `.xls`) - see the example file `metadata.csv.example`

### Step 2: Run Your Pipeline

Process your PDF as usual - the metadata will be automatically applied:

```bash
# If using the full pipeline
python3 pdf_to_unified_xml.py mybook.pdf --full-pipeline

# Or with custom metadata location
python3 pdf_to_unified_xml.py mybook.pdf --full-pipeline --metadata-dir /path/to/metadata/
```

**That's it!** Your Book.XML will now contain the complete BookInfo section with all your metadata.

## What If I Don't Have a Metadata File?

No problem! If the metadata file is not found, you'll see this message:

```
======================================================================
⚠ WARNING: Metadata file not available
======================================================================
  Could not find metadata.csv or metadata.xls/metadata.xlsx
  Book.xml may not be complete - using placeholder values
======================================================================
```

The pipeline will use placeholder values to ensure your Book.XML is still valid and passes DTD validation.

## Supported Metadata Fields

| Field | Example | Required? |
|-------|---------|-----------|
| ISBN | 978-1234567890 | Yes* |
| Title | "Professional Python" | Yes* |
| Subtitle | "Advanced Techniques" | No |
| Author | John Doe, Jane Smith | Yes* |
| Publisher | "Tech Books Inc." | Yes* |
| PublicationDate | 2024 | Yes* |
| Edition | "2nd Edition" | No |
| CopyrightYear | 2024 | No |
| CopyrightHolder | "Tech Books Inc." | No |

*Required fields will use placeholder values if not provided

## Multiple Authors

To specify multiple authors, just add multiple Author rows:

```csv
Field,Value
Author,John Doe
Author,Jane Smith
Author,Robert Johnson
```

Or use comma-separated values:
```csv
Field,Value
Author,John Doe, Jane Smith, Robert Johnson
```

## Excel Support

### For .xlsx files (modern Excel):
Already supported - no additional installation needed!

### For .xls files (legacy Excel):
Install the xlrd library:
```bash
pip install xlrd
```

## Troubleshooting

### Problem: "Cannot read Excel file"
**Solution:** Install required library:
```bash
pip install openpyxl  # for .xlsx files
pip install xlrd      # for .xls files
```

### Problem: Metadata not being applied
**Solutions:**
1. Check that your file is named exactly `metadata.csv`, `metadata.xlsx`, or `metadata.xls`
2. Make sure it's in the same directory as your PDF
3. Use `--metadata-dir` to specify the exact location

### Problem: "Metadata file is empty or invalid"
**Solutions:**
1. Verify your field names match the expected names (see table above)
2. Check that your file uses the correct format (see Step 1)
3. Ensure your file is saved with UTF-8 encoding

## Where to Find More Information

- **Full Documentation:** `METADATA_PROCESSOR_README.md`
- **Technical Details:** `METADATA_INTEGRATION_SUMMARY.md`
- **Example File:** `metadata.csv.example`
- **Test Suite:** `test_metadata_processor.py`

## Example: Complete Workflow

```bash
# 1. Create your metadata file
cat > metadata.csv << EOF
Field,Value
ISBN,978-0-123456-78-9
Title,Advanced Python Programming
Author,John Doe
Publisher,Tech Publishing
PublicationDate,2024
EOF

# 2. Process your PDF
python3 pdf_to_unified_xml.py mybook.pdf --full-pipeline

# 3. Check the output
unzip -q Output/mybook.zip
cat Book.XML | grep -A 20 "<bookinfo>"
```

You'll see your metadata perfectly formatted in the Book.XML file!

## Need Help?

Refer to the comprehensive documentation in `METADATA_PROCESSOR_README.md` for:
- Detailed field descriptions
- Advanced usage examples
- Programmatic API usage
- Complete troubleshooting guide

---

**Questions?** Check the documentation files or run the test suite to verify everything is working:
```bash
python3 test_metadata_processor.py
```
