# Table Extraction Quick Start Guide

## Problem Solved

Previously, 65 out of 86 detected tables were silently filtered out due to missing "Table X" captions. Now you have full control and visibility.

## What Changed

### 1. Enhanced Logging
You'll now see detailed information about:
- Which tables are being skipped
- Why they're being skipped (no caption, distance too far, etc.)
- Per-page summaries
- Overall extraction statistics

### 2. Command-Line Control
New flags let you control table filtering behavior

## Quick Usage Examples

### Example 1: Get ALL Tables (Recommended for now)

**Stop filtering tables by caption:**

```bash
# For media extraction only:
python Multipage_Image_Extractor.py document.pdf --no-caption-filter

# For full pipeline (unified XML):
python pdf_to_unified_xml.py document.pdf --no-caption-filter
```

This will extract all 86 tables without caption requirements. May include some false positives, but you won't miss any real tables.

### Example 2: Keep Caption Filtering (Default Behavior)

**Extract only tables with "Table X" captions nearby:**

```bash
# Current default behavior (no flags needed):
python Multipage_Image_Extractor.py document.pdf

# Or explicitly:
python pdf_to_unified_xml.py document.pdf
```

This is more conservative and filters out potential false positives.

### Example 3: Increase Caption Search Distance

**Allow captions that are further away from tables:**

```bash
# Allow captions up to 200 points away (default: 100):
python Multipage_Image_Extractor.py document.pdf --caption-distance 200

# For full pipeline:
python pdf_to_unified_xml.py document.pdf --caption-distance 200
```

This helps when tables have captions at the top of the page or other unusual layouts.

### Example 4: Combination - Relaxed but Not Disabled

```bash
# Keep caption filtering but be more lenient:
python pdf_to_unified_xml.py document.pdf --caption-distance 150
```

## What to Expect - New Output

### Media Extraction (Multipage_Image_Extractor.py)

**OLD OUTPUT:**
```
Stream flavor: 86 valid tables after filtering and deduplication
Total valid tables detected: 86
```
(No indication why only 21 appear in XML!)

**NEW OUTPUT:**
```
Stream flavor: 86 valid tables after filtering and deduplication
Total valid tables detected: 86

  Processing pages...
    Page 25: Skipping table 1 (bbox: 72.0,150.5,520.3,450.8) - no 'Table X' caption found within 100 points
    Page 42: Added 1 table(s), skipped 0 table(s)
    Page 53: Skipping table 1 (bbox: 80.2,200.1,510.5,380.4) - no 'Table X' caption found within 100 points
    ...

============================================================
Table Extraction Summary:
  Total tables detected by Camelot: 86
  Total tables written to media.xml: 21
  Tables filtered out: 65
  Reason: No 'Table X' caption found within 100 points
  Tip: Check the detailed logs above to see which tables were skipped
============================================================

XML metadata written to: document_MultiMedia.xml
Media saved under: document_MultiMedia/
```

### Unified XML Generation (pdf_to_unified_xml.py)

**NEW OUTPUT:**
```
Step 3: Parsing media data...
  ✓ Found media on 450 pages
  ✓ Found 21 tables across 18 pages

Step 5: Generating unified XML with page number IDs...
Unified XML saved to: document_unified.xml
  Pages: 997
  Tables: 21 (across 18 pages)
```

## Recommended Workflow

### Step 1: Run with No Caption Filter

```bash
python pdf_to_unified_xml.py document.pdf --no-caption-filter
```

This gets you all 86 tables.

### Step 2: Review the Results

Open the generated XML files and check if the additional 65 tables are legitimate:

```bash
# Count tables in media.xml:
grep -c '<table id=' document_MultiMedia.xml

# Count tables in unified.xml:
grep -c '<table reading_order=' document_unified.xml

# View a few table entries:
grep -A 5 '<table id=' document_MultiMedia.xml | head -30
```

### Step 3: Decide on Filtering Strategy

- **If most tables are legitimate**: Keep using `--no-caption-filter`
- **If many false positives**: Try `--caption-distance 150` or `--caption-distance 200`
- **If you want maximum precision**: Use default (caption required)

## Full Pipeline Example

```bash
# Full pipeline with all tables:
python pdf_to_unified_xml.py document.pdf \
  --full-pipeline \
  --no-caption-filter \
  --dpi 200

# Output will include:
# - document_unified.xml (with all tables)
# - document_MultiMedia.xml (with all tables)
# - document_structured.xml (DocBook format)
# - document_package.zip (deliverable)
```

## Understanding the Logs

### Table Skip Messages

```
Page 42: Skipping table 1 (bbox: 72.0,150.5,520.3,450.8) - no 'Table X' caption found within 100 points
```

- **Page 42**: Where the table was found
- **table 1**: First table detected on that page
- **bbox**: Bounding box coordinates (useful for debugging)
- **100 points**: Current search distance for captions

### Per-Page Summary

```
Page 42: Added 2 table(s), skipped 1 table(s)
```

Shows how many tables were kept vs. filtered on each page.

### Overall Summary

```
Table Extraction Summary:
  Total tables detected by Camelot: 86
  Total tables written to media.xml: 21
  Tables filtered out: 65
```

Shows the final counts - now you know exactly what happened!

## Troubleshooting

### Issue: Still only seeing 21 tables with --no-caption-filter

**Possible causes:**
1. Running old cached output - delete old XML files first:
   ```bash
   rm document_MultiMedia.xml document_unified.xml
   python pdf_to_unified_xml.py document.pdf --no-caption-filter
   ```

2. Wrong Python environment - make sure you're using the correct venv

### Issue: Too many false positive tables

**Solution:** Use caption filtering with increased distance:
```bash
python pdf_to_unified_xml.py document.pdf --caption-distance 150
```

Or examine the false positives and adjust the caption pattern matching code.

### Issue: Want different behavior for different pages

**Solution:** This requires code modification. Edit `Multipage_Image_Extractor.py` to add page-specific logic. For example:

```python
# Around line 1868 in add_tables_for_page:
if page_no in [42, 53, 98]:  # Specific pages with known good tables
    require_table_caption = False
else:
    require_table_caption = True
```

## Next Steps

1. Run with `--no-caption-filter` to get all 86 tables
2. Examine the results in media.xml and unified.xml
3. If quality is good, keep using `--no-caption-filter` as your default
4. If quality is poor, experiment with `--caption-distance` values

## Questions?

See `TABLE_FILTERING_ISSUE.md` for detailed technical explanation of the root cause and all available solutions.
