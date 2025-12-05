# Visual Flow: How Preprocessing and Column Detection Work Together

## The Complete Pipeline with Code Evidence

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: pdf_to_excel_columns.py (Lines 913-1287)                  │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                     │
│ INPUT: Raw PDF → pdftohtml -xml → XML with <text> fragments        │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 1A: Fragment-Level Preprocessing (lines 349-376)       │   │
│ │                                                              │   │
│ │ def should_skip_fragment(norm_txt, top, height, ...):       │   │
│ │     if top > page_height * 1.05:  # Outside page            │   │
│ │         return True                                          │   │
│ │     if re.search(r"\.indd\b", norm_txt):  # Print artifacts │   │
│ │         return True                                          │   │
│ │     if int(height) < 6:  # Invisible text                   │   │
│ │         return True                                          │   │
│ │     if top > page_height * 0.85 and norm_txt in footers:    │   │
│ │         return True  # Repeated footers                     │   │
│ │                                                              │   │
│ │ FILTERS: .indd, timestamps, tiny text, repeated footers     │   │
│ │ PURPOSE: Remove junk BEFORE column detection                │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 1B: Column Detection (lines 382-542)                   │   │
│ │                                                              │   │
│ │ def detect_column_starts(fragments, page_width, ...):       │   │
│ │     # 1D clustering of fragment left positions              │   │
│ │     clusters = cluster_by_x_position(fragments)             │   │
│ │                                                              │   │
│ │     # NEW: Vertical extent check                            │   │
│ │     for cluster in clusters:                                │   │
│ │         unique_baselines = count_lines(cluster)             │   │
│ │         if unique_baselines < 12:  # Not a real column!     │   │
│ │             discard_cluster(cluster)                        │   │
│ │                                                              │   │
│ │     return column_x_positions                               │   │
│ │                                                              │   │
│ │ def assign_column_ids(fragments, col_starts):               │   │
│ │     for f in fragments:                                     │   │
│ │         f["col_id"] = determine_column(f.left, col_starts)  │   │
│ │         # col_id: 0=full-width, 1,2,3,4=columns             │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 1C: Reading Order Assignment (lines 57-208)            │   │
│ │                                                              │   │
│ │ def assign_reading_order_from_rows(fragments, rows):        │   │
│ │     # Column-major order:                                   │   │
│ │     # 1. Full-width above columns (col_id=0)                │   │
│ │     # 2. Column 1 (top to bottom)                           │   │
│ │     # 3. Column 2 (top to bottom)                           │   │
│ │     # 4. Full-width below columns (col_id=0)                │   │
│ │                                                              │   │
│ │ def assign_reading_order_blocks(fragments, rows):           │   │
│ │     # Assign block numbers for reading flow                 │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ OUTPUT: Excel with col_id, reading_order_index, reading_block      │
│         Structured data dict with all fragment metadata            │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: pdf_to_unified_xml.py (lines 520-920)                     │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 2A: Call pdf_to_excel_columns (line 1275)              │   │
│ │                                                              │   │
│ │ result = pdf_to_excel_with_columns(pdf_path, ...)           │   │
│ │ pages_data = result["pages"]  # Contains col_id!            │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 2B: Extract Images/Tables (line 1285)                  │   │
│ │                                                              │   │
│ │ extract_media_and_tables(pdf_path, ...)                     │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 2C: Generate Unified XML (lines 790-920)               │   │
│ │                                                              │   │
│ │ # Group fragments into paragraphs                           │   │
│ │ for paragraph_group in merge_into_paragraphs(fragments):    │   │
│ │     para_elem = ET.SubElement(texts_elem, "para")           │   │
│ │                                                              │   │
│ │     # PRESERVE col_id from pdf_to_excel_columns (line 917)  │   │
│ │     para_elem.set("col_id",                                 │   │
│ │                   str(first_fragment["col_id"]))  ◄─────────│   │
│ │     para_elem.set("reading_block",                          │   │
│ │                   str(first_fragment["reading_order_block"]))   │
│ │                                                              │   │
│ │     for fragment in paragraph_group:                        │   │
│ │         text_elem = ET.SubElement(para_elem, "text")        │   │
│ │         # ... add text content ...                          │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ OUTPUT: unified.xml with structure:                                │
│   <page>                                                            │
│     <texts>                                                         │
│       <para col_id="1" reading_block="2">  ◄─── PRESERVED!         │
│         <text>Content here</text>                                  │
│       </para>                                                       │
│     </texts>                                                        │
│   </page>                                                           │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: heuristics_Nov3.py (lines 1704-2040)                      │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 3A: Document-Wide Preprocessing (lines 498-540)        │   │
│ │                                                              │   │
│ │ def _preprocess_xml_for_ebook(tree):                        │   │
│ │     # Phase 1: Remove duplicate/layered text                │   │
│ │     for page in tree.findall(".//page"):                    │   │
│ │         duplicates = _remove_duplicate_text(page)           │   │
│ │                                                              │   │
│ │     # Phase 2: Detect repeated patterns                     │   │
│ │     position_text = defaultdict(list)                       │   │
│ │     for page in tree.findall(".//page"):                    │   │
│ │         for text in page.findall("text"):                   │   │
│ │             norm_position = (top/height, left/width)        │   │
│ │             position_text[norm_position].append(text)       │   │
│ │                                                              │   │
│ │     # Find patterns that repeat 3+ times                    │   │
│ │     repeated_patterns = [text for pos, texts in ...         │   │
│ │                          if len(texts) >= 3]                │   │
│ │                                                              │   │
│ │ FINDS: Running headers, page numbers, repeated content      │   │
│ │ PURPOSE: Remove patterns not visible to fragment filter     │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 3B: Read Entries from Unified XML (lines 1704-1833)    │   │
│ │                                                              │   │
│ │ def _iter_page_entries_preserve(page, fontspec_map):        │   │
│ │     texts_elem = page.find("texts")                         │   │
│ │     if texts_elem is not None:  # Unified XML format        │   │
│ │         for para_elem in texts_elem.findall("para"):        │   │
│ │                                                              │   │
│ │             # READ col_id from unified XML (line 1741)      │   │
│ │             para_col_id = para_elem.get("col_id")  ◄─────── │   │
│ │             para_reading_block = para_elem.get(...)         │   │
│ │                                                              │   │
│ │             for text_elem in para_elem.findall("text"):     │   │
│ │                 entry = {...}                               │   │
│ │                                                              │   │
│ │                 # REUSE col_id (line 1778) - NO RE-DETECT!  │   │
│ │                 if para_col_id is not None:                 │   │
│ │                     entry["col_id"] = int(para_col_id)  ◄── │   │
│ │                                                              │   │
│ │                 entries.append(entry)                       │   │
│ │                                                              │   │
│ │ DOES NOT CALL: _reorder_lines_for_columns()                 │   │
│ │ DOES NOT CALL: _detect_page_columns()                       │   │
│ │ TRUSTS: Pre-computed col_id from pdf_to_excel_columns       │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 3C: Extract Bookmarks (lines 1028-1147)                │   │
│ │                                                              │   │
│ │ def _extract_bookmark_page_ranges(pdf_path):                │   │
│ │     reader = PdfReader(pdf_path)                            │   │
│ │     outlines = reader.outline                               │   │
│ │                                                              │   │
│ │     for item in outlines:                                   │   │
│ │         if isinstance(item, list): continue  # Skip nested  │   │
│ │         title = item.title                                  │   │
│ │         start_page = _get_page_number(item, reader)         │   │
│ │         bookmarks.append({title, start_page, end_page})     │   │
│ │                                                              │   │
│ │ UNIQUE TO HEURISTICS: Bookmark extraction                   │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │ Step 3D: Semantic Structure Analysis (lines 2050+)          │   │
│ │                                                              │   │
│ │ - Detect chapters (by bookmark or heuristic)                │   │
│ │ - Detect sections (font size hierarchy)                     │   │
│ │ - Detect lists (bullet/number patterns)                     │   │
│ │ - Detect TOC (page number patterns)                         │   │
│ │ - Detect index (alphabetical + page refs)                   │   │
│ │ - Label figures/tables (extract captions)                   │   │
│ │ - Group paragraphs                                          │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                              ↓                                      │
│ OUTPUT: Semantic DocBook XML with <chapter>, <section>, <para>,    │
│         <figure>, <table>, <itemizedlist>, etc.                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Code Evidence: Column Detection Reuse

### Evidence 1: pdf_to_unified_xml.py preserves col_id

```python
# Line 917 in pdf_to_unified_xml.py
para_elem.set("col_id", str(first_fragment["col_id"]))
#                              ↑
#                    From pdf_to_excel_columns
```

### Evidence 2: heuristics reads col_id from unified XML

```python
# Line 1741 in heuristics_Nov3.py
para_col_id = para_elem.get("col_id")  # Read from unified XML

# Line 1778 in heuristics_Nov3.py
if para_col_id is not None:
    entry["col_id"] = int(para_col_id)  # Reuse it!
```

### Evidence 3: heuristics trusts document order

```python
# Lines 2011-2025 in heuristics_Nov3.py
texts_elem = page.find("texts")
has_unified_format = texts_elem is not None

if not has_unified_format:
    # Old pdftohtml format - need to sort/reorder
    if not any((e.get("flow_idx", -1) >= 0) for e in page_entries):
        page_entries.sort(key=lambda e: (e.get("top", ...), ...))
# else: unified.xml format - TRUST DOCUMENT ORDER ◄─────────
#       Already sorted by reading_order in pdf_to_unified_xml.py
```

### Evidence 4: Column re-detection ONLY for legacy XML

```python
# Lines 1865-1869 in heuristics_Nov3.py
def _iter_page_entries(page, fontspecs):
    lines = _parse_lines(page, fontspecs)
    lines = _reorder_lines_for_columns(lines)  # ◄── Only called for old XML
    #                                               (not unified XML!)
```

## Preprocessing Comparison

### Fragment-Level (pdf_to_excel_columns) vs Document-Level (heuristics)

```
┌──────────────────────────────────────────────────────────────┐
│ Fragment-Level Filter (pdf_to_excel_columns)                 │
├──────────────────────────────────────────────────────────────┤
│ Page 1:  "9780803694958.indd   10/18/18"  → FILTERED        │
│ Page 1:  "Chapter 1"                       → KEPT            │
│ Page 1:  "Introduction text..."           → KEPT            │
│ Page 2:  "9780803694958.indd   10/18/18"  → FILTERED        │
│ Page 2:  "Chapter 1" (running header)     → KEPT  ◄─── Oops!│
│                                                               │
│ Why kept on page 2? Filter only sees individual fragments    │
│ Doesn't know this is a repeated header from page 1           │
└──────────────────────────────────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────┐
│ Document-Level Filter (heuristics)                           │
├──────────────────────────────────────────────────────────────┤
│ Analysis across ALL pages:                                   │
│   "Chapter 1" appears at (top=50, left=300) on pages 1-20    │
│   → Detected as REPEATED PATTERN                             │
│   → Remove from pages 2-20, keep on page 1 only              │
│                                                               │
│ Page 1:  "Chapter 1" (actual heading)     → KEPT             │
│ Page 2:  "Chapter 1" (running header)     → FILTERED  ✓      │
│ Page 3:  "Chapter 1" (running header)     → FILTERED  ✓      │
│                                                               │
│ Why filtered? Global view sees pattern repetition            │
└──────────────────────────────────────────────────────────────┘
```

## Summary: No Duplication, Perfect Synergy

| Operation | Where | When | Purpose |
|-----------|-------|------|---------|
| **Fragment junk removal** | pdf_to_excel_columns | Before column detection | Remove obvious junk |
| **Column detection** | pdf_to_excel_columns | Early processing | Detect layout structure |
| **Reading order** | pdf_to_excel_columns | Early processing | Order text correctly |
| **col_id preservation** | pdf_to_unified_xml | XML generation | Pass to heuristics |
| **col_id reuse** | heuristics | Entry reading | Use pre-computed values |
| **Document-wide patterns** | heuristics | After XML load | Remove repeated headers |
| **Bookmark extraction** | heuristics | Before structure | Chapter boundaries |
| **Semantic structure** | heuristics | Final stage | DocBook generation |

**Result:** Each stage does unique work, no duplication! ✅
