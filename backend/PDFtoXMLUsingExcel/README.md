# PDF to XML with Perfect Reading Order

Convert PDF files to structured XML with intelligent multi-column reading order detection, media extraction (images, tables, vectors), and hierarchical output suitable for HTML conversion.

## Overview

This toolkit processes PDF files through multiple stages to produce a unified XML file with perfect reading order:

1. **Text Extraction** - Uses `pdftohtml` to extract text with positioning
2. **Column Detection** - Intelligently detects single/multi-column layouts
3. **Reading Order** - Assigns correct reading sequence (left column → right column)
4. **Reading Blocks** - Groups content into logical blocks for sequential reading
5. **Media Extraction** - Extracts images, tables, and vector graphics
6. **Unified XML** - Merges text and media with correct reading order

## Features

- ✅ **Multi-column layout detection** (up to 4 columns)
- ✅ **Smart reading order** (Option A: read columns fully top-to-bottom)
- ✅ **Reading block assignment** (groups content into logical sections)
- ✅ **Full-width content handling** (headers, footers, callouts)
- ✅ **Media extraction** (raster images, vector graphics, tables)
- ✅ **Table detection with cell-level metadata** (bounding boxes, fonts, colors)
- ✅ **Text cleaning** (removes headers, footers, spine text, timestamps, artifacts)
- ✅ **Fragment merging** (joins split inline text)
- ✅ **Excel output** for debugging and verification
- ✅ **Hierarchical XML** output ready for HTML conversion

## Requirements

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y poppler-utils ghostscript

# macOS
brew install poppler ghostscript

# Windows
# Download and install Poppler from: https://github.com/oschwartz10612/poppler-windows/releases
# Add poppler/bin to your PATH
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install openpyxl PyMuPDF camelot-py[base] pypdf pandas numpy cffi
```

## Installation

```bash
# Clone the repository
git clone https://github.com/JCZentrovia/PDFtoXMLUsingExcel.git
cd PDFtoXMLUsingExcel

# Install Python dependencies
pip install -r requirements.txt

# Verify pdftohtml is installed
pdftohtml -v
```

## Usage

### Quick Start

Process a PDF file with default settings:

```bash
python3 pdf_to_unified_xml.py your-document.pdf
```

### Advanced Options

```bash
# With custom DPI for image rendering (default: 200)
python3 pdf_to_unified_xml.py your-document.pdf --dpi 300

# Specify output directory
python3 pdf_to_unified_xml.py your-document.pdf --out /path/to/output
```

### Output Files

Running the script generates the following files:

```
your-document_columns.xlsx          # Excel with 4 sheets (ReadingOrder, Lines, Images, Debug)
your-document_unified.xml           # ⭐ MAIN OUTPUT - Hierarchical XML with text + media
your-document_MultiMedia.xml        # Media metadata (images, tables, vectors)
your-document_MultiMedia/           # Folder containing all extracted media files
  ├── SharedImages/                 # Deduplicated raster images
  │   ├── img_xref123.png
  │   └── img_xref456.jpeg
  ├── page1_table1.png              # Table renderings
  ├── page2_vector1.png             # Vector graphic snapshots
  └── ...
your-document_pdftohtml.xml         # Raw pdftohtml output (for reference)
your-document_pdftohtml_original.xml # Backup of raw XML
```

## Excel Output (for Debugging)

The Excel file contains 4 sheets:

### 1. ReadingOrder Sheet
Contains all text fragments with reading order metadata:
- **Page** - Page number
- **StreamIndex** - Original order from pdftohtml
- **ReadingOrder** - Correct reading sequence (1, 2, 3...)
- **ReadingOrderBlock** - Logical block number (resets per page)
- **ColID** - Column assignment (0=full-width, 1=left, 2=right, etc.)
- **RowIndex** - Row/line number
- **Left, Top, Width, Height** - Bounding box
- **Baseline** - Vertical baseline position
- **Text** - Text content

### 2. Lines Sheet
Text grouped by rows and columns:
- Groups fragments into visual lines
- Shows column distribution (Col0_Text, Col1_Text, Col2_Text, etc.)

### 3. Images Sheet
Placeholder information for images

### 4. Debug Sheet
Raw fragment data for troubleshooting

## Unified XML Structure

The main output file (`*_unified.xml`) has a hierarchical structure:

```xml
<document source="filename.pdf">
  <page number="1" width="916.0" height="1188.0">

    <!-- Text fragments with reading order -->
    <texts>
      <text reading_order="1" reading_block="1" col_id="0" row_index="1"
            baseline="79.0" left="359.0" top="46.0" width="511.0" height="33.0"
            font="0" size="33">
        BOOK TITLE
      </text>
      <text reading_order="2" reading_block="2" col_id="1" row_index="2" ...>
        Left column text...
      </text>
      <text reading_order="50" reading_block="3" col_id="2" row_index="25" ...>
        Right column text...
      </text>
    </texts>

    <!-- Media elements (images, vectors) -->
    <media>
      <media reading_order="15.5" reading_block="2"
             id="p1_img_xref107" type="raster"
             file="SharedImages/img_xref107.png"
             x1="100.0" y1="200.0" x2="400.0" y2="500.0"
             alt="" title="Figure caption">
        <caption>Figure caption text</caption>
        <link href="http://example.com"/>
      </media>
    </media>

    <!-- Tables with cell-level metadata -->
    <tables>
      <table reading_order="60.5" reading_block="4"
             id="p1_table1" file="page1_table1.png"
             x1="50.0" y1="600.0" x2="550.0" y2="800.0"
             title="Table 1" alt="">
        <caption>Table caption text</caption>
        <rows>
          <row index="0">
            <cell index="0" x1="50.0" y1="600.0" x2="150.0" y2="620.0">
              <chunk font="Times-Roman" size="10.0" color="#000000">Cell text</chunk>
            </cell>
            <cell index="1" x1="150.0" y1="600.0" x2="250.0" y2="620.0">
              <chunk font="Times-Bold" size="10.0" color="#000000">Header</chunk>
            </cell>
          </row>
        </rows>
      </table>
    </tables>

  </page>
</document>
```

## Reading Order Logic

### Reading Block Assignment (Option A)

The script assigns reading blocks per page as follows:

1. **Block 1** - Full-width content ABOVE columns (headers, titles)
2. **Block 2** - Left column (all col_id=1 content, top to bottom)
3. **Block 3** - Right column (all col_id=2 content, top to bottom)
4. **Block 4+** - Additional columns if present
5. **Block N** - Full-width content BELOW/WITHIN columns (footnotes, callouts)

**Key principle:** Each column is read completely from top to bottom before moving to the next column.

### Column Detection

- Automatically detects 1-4 columns per page
- Uses X-position clustering to identify column boundaries
- Filters out false positives (vertical spine text, small clusters)
- Assigns `col_id`:
  - `0` = Full-width content (spans >45% of page width)
  - `1, 2, 3, 4` = Individual columns

### Text Cleaning

Automatically removes:
- Vertical spine text (e.g., "INTRODUCTION" on page margins)
- Print artifacts (.indd files, timestamps)
- Invisible/tiny text (height < 6px)
- Headers and footers (repeated text in margins)
- Crop marks and registration marks

### Fragment Merging

Inline text fragments are intelligently merged using a 2-step rule:
1. **No-gap merge**: If gap ≤ 1.5 points → merge
2. **Space-gap merge**: If text starts with space AND gap ≈ 1.0 point (±1.5) → merge

## Individual Scripts

While `pdf_to_unified_xml.py` is the recommended entry point, you can also run individual scripts:

### pdf_to_excel_columns.py
Extract text with reading order to Excel:
```bash
python3 pdf_to_excel_columns.py input.pdf [--xml output.xml] [--excel output.xlsx]
```

### Multipage_Image_Extractor.py
Extract media only:
```bash
python3 Multipage_Image_Extractor.py input.pdf [--dpi 200] [--out output_folder]
```

## Workflow Diagram

```
PDF Input
    ↓
┌─────────────────────────────────────┐
│ Step 1: pdftohtml -xml              │
│ Extract text with positions         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 2: pdf_to_excel_columns.py     │
│ - Detect columns                    │
│ - Assign reading order              │
│ - Assign reading blocks             │
│ - Clean & merge fragments           │
│ - Output Excel for debugging        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 3: Multipage_Image_Extractor   │
│ - Extract raster images             │
│ - Extract vector graphics           │
│ - Detect & extract tables           │
│ - Generate media XML                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 4: Merge & Generate            │
│ - Remove overlapping text           │
│ - Assign reading order to media     │
│ - Generate unified hierarchical XML │
└─────────────────────────────────────┘
    ↓
Unified XML Output
(Ready for HTML conversion)
```

## Example: Processing a Medical Textbook

```bash
# Process a medical textbook with high-quality images
python3 pdf_to_unified_xml.py medical-textbook.pdf --dpi 300

# Output files:
# - medical-textbook_unified.xml       (main output)
# - medical-textbook_columns.xlsx      (debugging)
# - medical-textbook_MultiMedia/       (images, tables)
```

### Verify Output

```bash
# Check Excel to verify reading order
libreoffice medical-textbook_columns.xlsx

# Check unified XML structure
xmllint --format medical-textbook_unified.xml | less

# View extracted images
ls medical-textbook_MultiMedia/
```

## Troubleshooting

### Issue: "pdftohtml: command not found"
**Solution:** Install poppler-utils (see Requirements section)

### Issue: "ModuleNotFoundError: No module named 'openpyxl'"
**Solution:** Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Reading order incorrect for complex layouts
**Solution:** Check the Excel output (ReadingOrder sheet) to debug:
- Verify `ColID` assignments
- Check `ReadingOrderBlock` values
- Review `Baseline` and positioning data

### Issue: Media overlapping with text
**Solution:** The script removes text whose center overlaps with media. If this isn't working correctly, check the media bounding boxes in the `*_MultiMedia.xml` file.

### Issue: Table detection missing tables
**Solution:** Camelot uses 'lattice' flavor by default (detects table borders). For tables without borders, you may need to modify `Multipage_Image_Extractor.py` line 379 to use `flavor="stream"`.

## Advanced Configuration

### Adjusting Column Detection

Edit `pdf_to_excel_columns.py`:

```python
# Line 283: Change max columns (default: 4)
def detect_column_starts(fragments, page_width, max_cols=4, ...):

# Line 286: Adjust minimum cluster size (default: 15)
min_cluster_size=15

# Line 287: Adjust minimum cluster ratio (default: 10%)
min_cluster_ratio=0.10
```

### Adjusting Fragment Merging

Edit `pdf_to_excel_columns.py` line 172:

```python
# Change gap tolerance (default: 1.5 points)
def merge_inline_fragments_in_row(row, gap_tolerance=1.5, space_width=1.0):
```

### Adjusting Text Filtering

Edit `pdf_to_excel_columns.py` line 269:

```python
# Change minimum height threshold (default: 6px)
if int(height) < 6:
```

## Performance

Typical processing times (on modern hardware):

- **100-page document**: ~2-3 minutes
- **500-page document**: ~10-15 minutes
- **1000-page document**: ~20-30 minutes

Factors affecting performance:
- Page count
- Number of images/tables
- PDF complexity (vector graphics)
- DPI setting for rendering

## Limitations

1. **OCR not included** - PDFs must have text layer (not scanned images)
2. **Complex layouts** - Very complex multi-column layouts may need manual review
3. **Rotated text** - Text rotated at arbitrary angles may not be handled correctly
4. **Nested tables** - Tables within tables may not be detected properly
5. **Watermarks** - May appear as overlapping text/media

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style
- New features include documentation
- Test with sample PDFs before submitting

## License

[Add your license information here]

## Credits

Built using:
- [Poppler](https://poppler.freedesktop.org/) - PDF rendering
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing
- [Camelot](https://camelot-py.readthedocs.io/) - Table detection
- [openpyxl](https://openpyxl.readthedocs.io/) - Excel generation

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
