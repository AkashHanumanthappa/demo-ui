# RittDoc DTD Compliance Pipeline - Complete Guide

## Overview

This comprehensive pipeline automatically converts XML DocBook packages to fully **RittDoc DTD-compliant** format with automatic validation, error fixing, and reporting.

## What It Does

The pipeline performs these operations automatically:

1. **Initial Validation** - Validates XML against RittDoc DTD and reports all errors
2. **Comprehensive Fixing** - Applies intelligent fixes to resolve DTD violations:
   - Wraps direct chapter content in proper `sect1` sections
   - Removes empty/placeholder figures and mediaobjects
   - Converts misclassified figures (with "table" in title) to paragraphs
   - Fixes nested para elements (preserves links and formatting)
   - Removes empty table rows
   - Adds missing required titles
   - Fixes missing required attributes (like `cols` in `tgroup`)
   - Normalizes whitespace
3. **Iterative Validation** - Re-validates after fixes and iterates until compliant
4. **TOC Generation** - Adds Table of Contents to Book.XML
5. **Final Report** - Generates Excel validation report with any remaining issues

## Key Files and Their Purpose

### Core Pipeline Scripts

1. **`rittdoc_compliance_pipeline.py`** - Main orchestration script
   - Coordinates the entire validation and fixing process
   - Runs multiple iterations if needed
   - Generates final compliant package

2. **`comprehensive_dtd_fixer.py`** - Intelligent DTD fixer
   - Fixes all common DTD validation errors
   - Preserves content while fixing structure
   - Tracks verification items for manual review

3. **`validate_with_entity_tracking.py`** - Entity-aware validator
   - Validates each chapter file individually
   - Reports actual source file and line numbers
   - Handles entity references correctly

4. **`validation_report.py`** - Excel report generator
   - Creates human-readable validation reports
   - Categorizes errors by type
   - Includes manual verification tracking

### Supporting Scripts

5. **`add_toc_to_book.py`** - TOC generator
   - Adds proper `<toc>` element to Book.XML
   - Extracts chapter titles automatically
   - Creates DTD-compliant TOC structure

6. **`fix_chapter_dtd_violations.py`** - Simple chapter fixer (alternative)
   - Lightweight version for basic violations
   - Wraps content in sect1 sections
   - No lxml dependency required

7. **`fix_misclassified_figures.py`** - Figure-to-table converter
   - Detects figures that should be tables
   - Preserves captions and structure
   - Removes empty figures

8. **`validate_rittdoc.py`** - Basic validation script
   - Simple validation without entity tracking
   - Can transform with XSLT before validation

9. **`xslt_transformer.py`** - XSLT transformation module
   - Applies XSLT transformations for compliance
   - Converts generic DocBook to RittDoc format

10. **`xslt/rittdoc_compliance.xslt`** - XSLT stylesheet
    - Transforms `<info>` to `<bookinfo>`
    - Converts `<section>` to numbered `<sect1>`-`<sect5>`
    - Ensures required elements exist
    - Removes banned elements (variablelist, informalfigure, etc.)

## Understanding the RittDoc DTD

### Key Requirements

The RittDoc DTD (based on DocBook 4.2) has specific requirements:

1. **Chapter Structure**
   ```xml
   <chapter id="required-id">
     <title>Required Title</title>
     <sect1 id="required-id">
       <title>Required Title</title>
       <para>Content goes here</para>
     </sect1>
   </chapter>
   ```

2. **No Direct Content in Chapters**
   - Chapters CANNOT have `<para>`, `<figure>`, `<table>` as direct children
   - All content must be wrapped in `<sect1>` sections
   - Chapter content model: `(title, tocchap?, (toc|lot|index|glossary|bibliography|sect1)*)`

3. **No Nested Para Elements**
   - `<para>` cannot contain other `<para>` elements
   - The fixer intelligently unwraps or flattens nested paras

4. **Required Attributes**
   - Sections must have `id` attributes
   - Table `<tgroup>` must have `cols` attribute
   - Image `<imagedata>` must have `fileref` attribute

5. **Banned Elements**
   - `variablelist`, `varlistentry` → use `glosslist`, `glossentry`
   - `informalfigure` → use `figure` with title
   - `informaltable` → use `table` with title

6. **BookInfo Requirements**
   - Must have: `title`, `author`, `publisher`, `isbn`, `copyright` with `year`

## Usage

### Basic Usage

Process an existing XML DocBook package:

```bash
python3 rittdoc_compliance_pipeline.py mybook.zip
```

This creates:
- `mybook_rittdoc_compliant.zip` - Fully compliant package
- `mybook_rittdoc_compliant_validation_report.xlsx` - Validation report (if errors remain)

### Advanced Options

```bash
# Custom output path
python3 rittdoc_compliance_pipeline.py mybook.zip --output mybook_final.zip

# Custom DTD
python3 rittdoc_compliance_pipeline.py mybook.zip --dtd path/to/custom.dtd

# More iterations (default is 3)
python3 rittdoc_compliance_pipeline.py mybook.zip --iterations 5
```

### Running Tests

Test the pipeline with sample data:

```bash
# Quick demo with simple test
python3 quick_demo.py

# Realistic test with DTD violations
python3 create_realistic_test.py
```

### Processing PDF Files

To create a compliant package from a PDF:

```bash
# Step 1: Generate XML from PDF
python3 pdf_to_unified_xml.py document.pdf

# Step 2: Create DocBook package
python3 package.py document_unified.xml

# Step 3: Make it RittDoc compliant
python3 rittdoc_compliance_pipeline.py Output/document.zip
```

## Common DTD Violations and Fixes

### Violation 1: Direct Content in Chapter

**Error:**
```
Element chapter content does not match what the DTD expects
```

**Cause:**
```xml
<chapter id="ch01">
  <title>Chapter 1</title>
  <para>Direct paragraph (VIOLATION)</para>
</chapter>
```

**Fix Applied:**
```xml
<chapter id="ch01">
  <title>Chapter 1</title>
  <sect1 id="ch01-intro">
    <title>Introduction</title>
    <para>Direct paragraph (now wrapped)</para>
  </sect1>
</chapter>
```

### Violation 2: Nested Para Elements

**Error:**
```
Element para is not declared in para list of possible children
```

**Cause:**
```xml
<para>Outer text.
  <para>Nested para (VIOLATION)</para>
</para>
```

**Fix Applied:**
- If nested para has only inline content (links, emphasis):
  → Unwraps and merges into parent para
- If nested para has block content (lists, tables):
  → Flattens into sibling paras

### Violation 3: Empty Figure

**Error:**
```
Element figure content does not match what the DTD expects
```

**Cause:**
```xml
<figure id="fig1">
  <title>Empty Figure</title>
  <!-- No mediaobject or graphic -->
</figure>
```

**Fix Applied:**
- If figure has no title or empty title → Removes completely
- If figure has "table" in title → Converts to para
- Otherwise → Removes and logs

### Violation 4: Misclassified Figure

**Pattern:**
```xml
<figure>
  <title>Table 10.9–3 Examples</title>
  <mediaobject><textobject><phrase>Image not available</phrase></textobject></mediaobject>
</figure>
<table>
  <title>Table 1</title>
  <tgroup cols="2">...</tgroup>
</table>
```

**Fix Applied:**
```xml
<table>
  <title>Table 10.9–3 Examples</title>
  <tgroup cols="2">...</tgroup>
</table>
```

### Violation 5: Missing Required Attributes

**Error:**
```
Missing required attribute: cols
```

**Cause:**
```xml
<tgroup>  <!-- Missing cols attribute -->
  <tbody>...</tbody>
</tgroup>
```

**Fix Applied:**
```xml
<tgroup cols="2">  <!-- Auto-detected from first row -->
  <tbody>...</tbody>
</tgroup>
```

## Output Files

### Compliant Package (ZIP)

Contains:
- `Book.XML` - Main book file with entity references
- `ch0001.xml`, `ch0002.xml`, ... - Individual chapter files (all compliant)
- `RITTDOCdtd/` - DTD files (if copied from source)
- Media files (images, etc.)

### Validation Report (Excel)

Three sheets:

1. **Summary** - Overview statistics
   - Total errors by severity
   - Top error types
   - Validation status

2. **Validation Errors** - Detailed error list
   - File name and line number
   - Error type and description
   - Severity (Error/Warning/Info)

3. **Manual Verification** - Items requiring review
   - Auto-generated titles
   - Converted structures
   - Suggested actions

## Verification Items

Some fixes create content that should be manually verified:

| Fix Type | Verification Needed | Suggestion |
|----------|-------------------|------------|
| Missing Title | Auto-generated generic title | Update with descriptive title |
| Wrapped Content | Generic "Introduction" section created | Review and update section title |
| Nested Para Fix | Content was unwrapped/flattened | Verify links and formatting preserved |
| Figure Conversion | Figure converted to para or table | Verify structure is correct |

## Pipeline Statistics

After running, you'll see:

```
Files processed:        15
Files fixed:            12
Total fixes applied:    47
Validation iterations:  2

Initial errors:         52
Final errors:           0
Errors fixed:           52
Improvement:            100.0%
```

## Success Criteria

✓ **Full Success**: 0 final errors, 100% improvement
⚠ **Partial Success**: Reduced errors, manual review needed
✗ **Failed**: No improvement or errors increased

## Troubleshooting

### No Improvement After Iteration

If errors don't decrease after an iteration:
- Check validation report for specific error types
- Some errors may require manual fixes
- Consider running individual fix scripts

### Entity Reference Errors

If you see "Entity not defined" errors:
- Ensure all chapter files are in the ZIP
- Check DOCTYPE declaration has all entities
- Verify entity filenames match actual files

### Missing Dependencies

If you see import errors:
```bash
pip install lxml openpyxl
```

## Integration with Existing Workflow

### Current PDF Processing Workflow

```
PDF → pdf_to_unified_xml.py → Unified XML → package.py → DocBook ZIP
```

### Complete Workflow with RittDoc Compliance

```
PDF → pdf_to_unified_xml.py → Unified XML → package.py → DocBook ZIP
                                                             ↓
                               rittdoc_compliance_pipeline.py
                                                             ↓
                                              RittDoc Compliant ZIP ✓
```

## Best Practices

1. **Always Keep Backups**
   - The pipeline creates new ZIP files, doesn't modify originals
   - Original: `mybook.zip`
   - Output: `mybook_rittdoc_compliant.zip`

2. **Review Verification Items**
   - Check the "Manual Verification" sheet in the Excel report
   - Update auto-generated titles for better readability

3. **Iterative Improvement**
   - Start with max_iterations=3 (default)
   - If needed, increase to 5 for complex documents

4. **Validate Early**
   - Run validation on sample chapters during development
   - Catch issues before processing entire book

## DTD File Locations

- **Main DTD**: `RITTDOCdtd/v1.1/RittDocBook.dtd`
- **Hierarchy Module**: `RITTDOCdtd/v1.1/ritthier2.mod`
- **Custom Tags**: `RITTDOCdtd/v1.1/rittcustomtags.mod`
- **Demo XML**: `RITTDOCdtd/v1.1/demo.xml`

## Additional Resources

- **DocBook 4.2 Spec**: https://docbook.org/specs/docbook-4.2.html
- **lxml Documentation**: https://lxml.de/
- **RittDoc Modifications**: See `RITTDOCdtd/v1.1/Notes on Modifying DocBook.doc`

## Support and Contribution

For issues or improvements:
1. Check validation report for specific error details
2. Review this guide for common violations
3. Test with `create_realistic_test.py` for debugging

---

**Last Updated**: November 2024
**Version**: 1.0
**Compatibility**: Python 3.8+, RittDoc DTD v1.1
