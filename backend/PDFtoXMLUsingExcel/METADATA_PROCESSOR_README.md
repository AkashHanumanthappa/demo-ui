# Metadata Processor for Book.XML

## Overview

The metadata processor automatically populates the BookInfo section of Book.XML files with metadata from CSV or Excel files. This ensures that book metadata (ISBN, title, authors, publisher, etc.) is accurately captured in the final DocBook package.

## Metadata File Format

### File Naming
The metadata processor looks for files named:
- `metadata.csv`
- `metadata.xlsx`
- `metadata.xls`

Place the metadata file in the same directory as your PDF file.

### Supported Formats

#### Option 1: Vertical Format (Recommended)
Two columns with Field names in the first column and Values in the second:

```csv
Field,Value
ISBN,978-1234567890
Title,Sample Book Title
Subtitle,A Comprehensive Guide
Author,John Doe
Author,Jane Smith
Publisher,Sample Publishing House
PublicationDate,2024
Edition,2nd Edition
CopyrightYear,2024
CopyrightHolder,Sample Publishing House
```

#### Option 2: Horizontal Format
Field names in the first row, values in subsequent rows:

```csv
ISBN,Title,Author,Publisher,PublicationDate
978-1234567890,Sample Book Title,John Doe,Sample Publishing,2024
```

### Supported Fields

| Field Name | Aliases | Required | Description |
|------------|---------|----------|-------------|
| ISBN | isbn, isbn13, isbn-13, isbn10, isbn-10 | Yes* | Book ISBN (hyphens/spaces removed automatically) |
| Title | title, book_title, booktitle | Yes* | Main book title |
| Subtitle | subtitle, sub_title, book_subtitle | No | Book subtitle (optional) |
| Author | author, authors, author_name, by | Yes* | Author name(s) - multiple rows for multiple authors |
| Publisher | publisher, publishername, publisher_name | Yes* | Publisher name |
| PublicationDate | pubdate, publication_date, date, published, year | Yes* | Publication year or date |
| Edition | edition, edition_number | No | Edition (e.g., "1st Edition", "2nd Edition") |
| CopyrightYear | copyright_year, copyrightyear, copyright | No | Copyright year |
| CopyrightHolder | copyright_holder, copyrightholder, holder | No | Copyright holder name |

*Required fields will use placeholder values if not provided to ensure DTD validation passes.

### Multiple Authors

To specify multiple authors, use multiple rows (in vertical format) or comma/semicolon-separated values:

**Vertical Format:**
```csv
Field,Value
Author,John Doe
Author,Jane Smith
Author,Robert Johnson
```

**Horizontal Format:**
```csv
Author
John Doe, Jane Smith, Robert Johnson
```

Or:
```csv
Author
John Doe; Jane Smith; Robert Johnson
```

## Integration with Pipeline

### Automatic Detection

The metadata processor is automatically invoked during the packaging step. It searches for metadata files in:

1. The explicitly provided metadata directory (if specified)
2. The output directory (where the ZIP package is created)
3. The current working directory
4. The PDF's directory

### Command-Line Usage

#### Full Pipeline with Metadata

```bash
# Process PDF with metadata in the same directory
python3 pdf_to_unified_xml.py mybook.pdf --full-pipeline

# Specify custom metadata location
python3 pdf_to_unified_xml.py mybook.pdf --full-pipeline --metadata-dir /path/to/metadata/
```

#### Standalone Metadata Processing

You can also run the metadata processor standalone to update an existing Book.XML:

```bash
python3 metadata_processor.py Book.XML /path/to/metadata/dir/
```

### Programmatic Usage

```python
from metadata_processor import populate_bookinfo_from_metadata
from pathlib import Path

# Populate BookInfo from metadata file
success = populate_bookinfo_from_metadata(
    book_xml_path=Path("Book.XML"),
    metadata_dir=Path("."),
    backup=True  # Create backup before modifying
)

if success:
    print("Metadata successfully applied!")
else:
    print("No metadata file found or processing failed")
```

## Behavior

### When Metadata File is Found

1. The processor reads the metadata file
2. Extracts all available metadata fields
3. Removes any existing `<bookinfo>` or `<info>` elements from Book.XML
4. Creates a new `<bookinfo>` element with the extracted metadata
5. Inserts it at the beginning of the Book.XML root element
6. Prints a summary of the applied metadata

**Output:**
```
======================================================================
✓ Successfully populated BookInfo from metadata
======================================================================
  Metadata file: metadata.csv
  ISBN: 978-1234567890
  Title: Sample Book Title
  Author(s): John Doe, Jane Smith
  Publisher: Sample Publishing House
  Date: 2024
======================================================================
```

### When Metadata File is NOT Found

1. A warning message is displayed
2. The Book.XML uses placeholder values to ensure DTD validation passes
3. Processing continues normally

**Output:**
```
======================================================================
⚠ WARNING: Metadata file not available
======================================================================
  Could not find metadata.csv or metadata.xls/metadata.xlsx
  Book.xml may not be complete - using placeholder values
  Expected location: /path/to/search/directory
======================================================================
```

### Placeholder Values

When metadata is missing, the following placeholder values are used:

- **ISBN:** `0000000000000`
- **Title:** `Untitled Book`
- **Author:** `Unknown Author`
- **Publisher:** `Unknown Publisher`
- **Publication Date:** `2024`
- **Edition:** `1st Edition`
- **Copyright Year:** Current year or publication date
- **Copyright Holder:** Publisher name or `Copyright Holder`

## Generated BookInfo XML Structure

The metadata processor generates a DocBook-compliant `<bookinfo>` element:

```xml
<bookinfo>
    <isbn>978-1234567890</isbn>
    <title>Sample Book Title</title>
    <subtitle>A Comprehensive Guide</subtitle>
    <authorgroup>
        <author>
            <personname>
                <firstname>John</firstname>
                <surname>Doe</surname>
            </personname>
        </author>
        <author>
            <personname>
                <firstname>Jane</firstname>
                <surname>Smith</surname>
            </personname>
        </author>
    </authorgroup>
    <publisher>
        <publishername>Sample Publishing House</publishername>
    </publisher>
    <pubdate>2024</pubdate>
    <edition>2nd Edition</edition>
    <copyright>
        <year>2024</year>
        <holder>Sample Publishing House</holder>
    </copyright>
</bookinfo>
```

## Installation Requirements

### For CSV Files
No additional requirements - uses Python's built-in `csv` module.

### For Excel Files

**For .xlsx files:**
```bash
pip install openpyxl
```

**For .xls files:**
```bash
pip install xlrd
```

Or install both:
```bash
pip install openpyxl xlrd
```

## Troubleshooting

### Error: "Cannot read Excel file"

**Problem:** Missing required library for Excel file format.

**Solution:** Install the appropriate library:
```bash
pip install openpyxl  # for .xlsx files
pip install xlrd      # for .xls files
```

### Warning: "Metadata file is empty or invalid"

**Problem:** Metadata file exists but contains no valid data.

**Solutions:**
1. Check that field names match the expected names (see Supported Fields table)
2. Verify that the file format is correct (vertical or horizontal)
3. Ensure the file is not empty
4. Check for encoding issues (use UTF-8 encoding)

### No Metadata Applied

**Problem:** Metadata file exists but is not being found.

**Solutions:**
1. Verify the filename is exactly `metadata.csv`, `metadata.xlsx`, or `metadata.xls`
2. Check that the file is in the same directory as your PDF
3. Use `--metadata-dir` to explicitly specify the directory
4. Check file permissions

## Best Practices

1. **Use CSV Format:** CSV files are simpler and more portable than Excel files
2. **Vertical Format:** The vertical (Field, Value) format is more readable for metadata
3. **UTF-8 Encoding:** Always save CSV files with UTF-8 encoding to support special characters
4. **Complete Metadata:** Provide all required fields to avoid placeholder values
5. **Version Control:** Keep metadata files in version control alongside your source PDFs

## Example Workflows

### Basic Workflow
```bash
# 1. Place PDF and metadata.csv in the same directory
# 2. Run the full pipeline
python3 pdf_to_unified_xml.py mybook.pdf --full-pipeline

# The metadata will be automatically applied during packaging
```

### Advanced Workflow
```bash
# 1. Separate source files from outputs
mkdir source output

# 2. Place PDF and metadata in source directory
mv mybook.pdf source/
mv metadata.csv source/

# 3. Run pipeline with explicit metadata directory
python3 pdf_to_unified_xml.py source/mybook.pdf \
    --out output/ \
    --metadata-dir source/ \
    --full-pipeline

# Metadata is applied from source/, output goes to output/
```

### Update Existing Book.XML
```bash
# If you already have a Book.XML and want to apply metadata
python3 metadata_processor.py path/to/Book.XML path/to/metadata/dir/
```

## Technical Details

### Metadata Extraction Order

1. **Explicit metadata directory** (if provided via `--metadata-dir` or `metadata_dir` parameter)
2. **Output directory** (where ZIP package is being created)
3. **Current working directory**
4. **PDF directory** (default)

The first metadata file found in this order is used.

### Name Parsing

Author names are automatically parsed:
- Multi-word names are split into firstname + surname
- The last word is treated as surname
- Everything before the last word is treated as firstname
- Single-word names are used as surname only

Examples:
- "John Doe" → firstname: "John", surname: "Doe"
- "Mary Jane Smith" → firstname: "Mary Jane", surname: "Smith"
- "Prince" → firstname: "", surname: "Prince"

### ISBN Cleaning

ISBNs are automatically cleaned:
- Hyphens removed
- Spaces removed
- Only digits and 'X' retained (for ISBN-10)
- Example: "978-1-234-56789-0" → "9781234567890"

## See Also

- [Main README](README.md) - Complete pipeline documentation
- [RittDoc Compliance Guide](RITTDOC_COMPLIANCE_GUIDE.md) - DTD validation information
- Example metadata file: [metadata.csv.example](metadata.csv.example)
