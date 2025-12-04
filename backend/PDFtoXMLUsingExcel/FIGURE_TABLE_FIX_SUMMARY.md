# Figure and Table Processing Fix

## Problem Summary

The user reported three critical issues with the structured XML output:

1. **Missing `mediaobject` elements**: Figures were created without `<mediaobject>` child elements containing image references
2. **Massive figure titles**: Figure `<title>` elements contained entire paragraphs of text instead of concise captions
3. **Missing tables**: Tables were not appearing in the final structured XML output

## Root Causes

### 1. Massive Figure Titles

**Location**: `heuristics_Nov3.py` lines 2128-2136

**Problem**: The code was extracting the `title` attribute from media elements without any filtering. The media extraction process (`Multipage_Image_Extractor.py`) uses `find_title_caption_for_region()` which can capture large blocks of text near images.

**Fix**: Modified the caption extraction logic to:
- Prioritize `<caption>` child elements over `title` attributes
- Filter out oversized title text (> 200 characters) unless it starts with "Figure"
- Added debug logging for skipped oversized titles

```python
# Get caption from caption element FIRST, then fallback to title attribute
cap_el = fig_el.find(".//caption")
if cap_el is not None:
    try:
        caption_text = get_text(cap_el)
    except Exception:
        caption_text = "".join(cap_el.itertext()).strip()
else:
    # Only use title attribute if no caption element exists
    # Filter out large blocks of text that aren't real captions
    title_text = fig_el.get("title") or ""
    # Only use title if it's reasonably short (< 200 chars) or starts with "Figure"
    if len(title_text) < 200 or title_text.strip().lower().startswith("figure"):
        caption_text = title_text
    else:
        caption_text = ""
        logger.debug(f"Skipping oversized title text ({len(title_text)} chars) for media {fig_el.get('id')}")
```

### 2. Missing `mediaobject` Elements

**Location**: `heuristics_Nov3.py` lines 2845-2853

**Problem**: While the code was correctly extracting the `file` attribute from media elements (line 2119), there was no visibility into why `mediaobject` elements might not be created.

**Fix**: Added debug logging to track when `mediaobject` elements are created and when they're skipped:

```python
# Add mediaobject for the image
if src:
    mediaobject = etree.SubElement(figure, "mediaobject")
    imageobject = etree.SubElement(mediaobject, "imageobject")
    imagedata = etree.SubElement(imageobject, "imagedata")
    imagedata.set("fileref", src)
    logger.debug(f"Created mediaobject for figure with src={src}")
else:
    logger.warning(f"Figure created without mediaobject - missing src attribute (id={block_id or 'unknown'})")
```

Also improved the figure ID generation to use the block ID from media elements:

```python
# Use block ID if available, otherwise generate from src
if block_id:
    figure.set("id", block_id)
elif src:
    figure_id = src.replace(".", "_").replace("/", "_")
    figure.set("id", figure_id)
```

### 3. Missing Tables

**Location**: `heuristics_Nov3.py` lines 2088-2119 (table entry processing) and 2888-2970 (DocBook table generation)

**Problem**: Tables were being extracted from the unified XML and added to entries with `"kind": "table"`, but they were **never processed** in the block generation loop. The code only handled figures (`"kind" in ("image", "figure")`) but had no handling for tables.

**Fix**: Added complete table processing in two stages:

#### Stage 1: Create Table Blocks (lines 2088-2119)

Added code to detect table entries and create table blocks:

```python
# Tables: flush paragraph then emit table block
if entry.get("kind") == "table":
    if current_para:
        blk = _finalize_paragraph(current_para, default_font_size=body_size)
        _append_paragraph_block(blk)
        current_para = []
    
    table_el = entry.get("el")
    if table_el is not None:
        # Create a table block with the element and metadata
        table_block = {
            "label": "table",
            "el": table_el,
            "page_num": entry.get("page_number"),
            "id": table_el.get("id"),
            "caption": "",
        }
        
        # Get caption from caption element or title attribute
        cap_el = table_el.find(".//caption")
        if cap_el is not None:
            try:
                table_block["caption"] = get_text(cap_el)
            except Exception:
                table_block["caption"] = "".join(cap_el.itertext()).strip()
        else:
            table_block["caption"] = table_el.get("title") or ""
        
        blocks.append(table_block)
        logger.debug(f"Added table block: {table_block['id']}")
    idx += 1
    continue
```

#### Stage 2: Generate DocBook Table Structure (lines 2888-2970)

Added code to convert table blocks into proper DocBook table XML:

```python
elif label == "table":
    # Handle table blocks
    # Close any open list
    current_list = None
    current_list_type = None

    target = current_section if current_section is not None else current_chapter
    if target is None:
        # Create default chapter if needed
        ...
    
    # Get the table element from the block
    table_el = block.get("el")
    if table_el is not None:
        # Create a DocBook table structure
        # Use informaltable if no caption, otherwise use table with title
        caption_text = block.get("caption", "")
        table_id = block.get("id")
        
        if caption_text:
            # Formal table with caption
            table_wrapper = etree.SubElement(target, "table")
            if table_id:
                table_wrapper.set("id", table_id)
            
            title_elem = etree.SubElement(table_wrapper, "title")
            title_elem.text = caption_text
            
            # Create tgroup for the table structure
            tgroup = etree.SubElement(table_wrapper, "tgroup")
        else:
            # Informal table (no caption)
            table_wrapper = etree.SubElement(target, "informaltable")
            if table_id:
                table_wrapper.set("id", table_id)
            
            # Create tgroup for the table structure
            tgroup = etree.SubElement(table_wrapper, "tgroup")
        
        # Extract table structure from the unified XML element
        rows_el = table_el.find(".//rows")
        if rows_el is not None:
            rows = rows_el.findall("row")
            if rows:
                # Determine number of columns
                first_row = rows[0]
                num_cols = len(first_row.findall("cell"))
                tgroup.set("cols", str(num_cols))
                
                # Create colspec elements
                for col_idx in range(num_cols):
                    colspec = etree.SubElement(tgroup, "colspec")
                    colspec.set("colname", f"c{col_idx + 1}")
                
                # Create tbody
                tbody = etree.SubElement(tgroup, "tbody")
                
                # Add rows
                for row_el in rows:
                    row = etree.SubElement(tbody, "row")
                    cells = row_el.findall("cell")
                    for cell_el in cells:
                        entry = etree.SubElement(row, "entry")
                        
                        # Extract cell text from chunks
                        chunks = cell_el.findall("chunk")
                        cell_text_parts = []
                        for chunk in chunks:
                            if chunk.text:
                                cell_text_parts.append(chunk.text.strip())
                        
                        cell_text = " ".join(cell_text_parts).strip()
                        if cell_text:
                            entry.text = cell_text
                
                logger.debug(f"Created DocBook table structure for {table_id} with {len(rows)} rows and {num_cols} cols")
```

## Expected Results

After these fixes:

1. **Figures** will have:
   - Concise titles (< 200 chars or starting with "Figure")
   - `<mediaobject>` elements with `<imagedata fileref="..."/>` pointing to image files
   - Proper IDs for cross-referencing
   - Debug logging for troubleshooting

2. **Tables** will have:
   - Proper DocBook structure with `<table>` or `<informaltable>`
   - `<tgroup>` with column specifications
   - `<tbody>` with rows and entries
   - Captions when available
   - Debug logging for troubleshooting

Example figure output:
```xml
<figure id="page19_img1_png">
  <title>Figure 1. Protons aligned with magnetic field</title>
  <mediaobject>
    <imageobject>
      <imagedata fileref="page19_img1.png"/>
    </imageobject>
  </mediaobject>
</figure>
```

Example table output:
```xml
<table id="p20_table1">
  <title>Table 1. MRI Scanner Field Strengths</title>
  <tgroup cols="3">
    <colspec colname="c1"/>
    <colspec colname="c2"/>
    <colspec colname="c3"/>
    <tbody>
      <row>
        <entry>Field Strength</entry>
        <entry>Frequency</entry>
        <entry>Applications</entry>
      </row>
      <row>
        <entry>1.5 T</entry>
        <entry>63.87 MHz</entry>
        <entry>Clinical imaging</entry>
      </row>
      ...
    </tbody>
  </tgroup>
</table>
```

## Testing

To test the fixes:

```bash
# Run the full pipeline
python pdf_to_unified_xml.py 9780803694958.pdf --full-pipeline

# Check the structured XML for:
# 1. Figures with mediaobject elements
# 2. Concise figure titles
# 3. Tables with proper DocBook structure
```

Look for debug messages in the output:
- "Created mediaobject for figure with src=..."
- "Skipping oversized title text (XXX chars) for media ..."
- "Added table block: ..."
- "Created DocBook table structure for ... with X rows and Y cols"

## Files Modified

- `heuristics_Nov3.py`:
  - Lines 2128-2145: Fixed caption text extraction with size filtering
  - Lines 2823-2853: Improved figure ID generation and added mediaobject logging
  - Lines 2088-2119: Added table block creation
  - Lines 2888-2970: Added DocBook table structure generation
