# Solution Plan: Three Critical Fixes

## Overview

This document outlines the implementation plan for three critical fixes:

1. **Fragment Tracking with RittDocDTD Compliance**
2. **Fix Aggressive Para Grouping with Vertical Gap Detection**
3. **Image/Table Page-to-Chapter Reference Mapping**

## Fix 1: RittDocDTD-Compliant Fragment Tracking

### Problem
- Currently losing font/size metadata when merging fragments
- Proposed solution used custom `<fragments>` element (NOT DTD-compliant)

### Solution: Use Inline Elements

According to RittDocDTD (dbpoolx.mod):
- `<para>` can contain `%para.char.mix;` (inline elements)
- Available inline elements: `<phrase>`, `<emphasis>`, `<subscript>`, `<superscript>`
- These can be nested to preserve formatting

### RittDocDTD Structure

```
<!ELEMENT para %ho; (%para.char.mix; | %para.mix;)*>
<!ELEMENT phrase %ho; (%para.char.mix;)*>
<!ELEMENT emphasis %ho; (%para.char.mix;)*>
<!ELEMENT subscript %ho; (#PCDATA
<!ELEMENT superscript %ho; (#PCDATA
```

### Implementation Strategy

Use `<phrase>` with custom attributes to track original fragments:

```xml
<para>
  <!-- Merged text for readability -->
  The formula H₂O
  
  <!-- But use nested phrase elements to preserve metadata -->
  <phrase role="original-fragment" font="3" size="12" stream-index="1">The formula H</phrase>
  <subscript font="3" size="8" stream-index="2">₂</subscript>
  <phrase role="original-fragment" font="3" size="12" stream-index="3">O</phrase>
</para>
```

**Better approach - just use inline elements directly:**

```xml
<para>
  <phrase font="3" size="12">The formula H</phrase><subscript font="3" size="8">₂</subscript><phrase font="3" size="12">O</phrase>
</para>
```

**For mixed fonts (like bold/italic):**

```xml
<para>
  <phrase font="3">Hello </phrase><emphasis font="5">world</emphasis><phrase font="3">!</phrase>
</para>
```

### Code Changes Required

**File: `pdf_to_unified_xml.py`**

Modify `create_unified_xml()` function to output inline elements instead of plain text:

```python
# Instead of:
text_elem.text = f["text"]

# Do:
for frag in f["original_fragments"]:
    # Determine appropriate element based on fragment properties
    if frag.get("is_script"):
        if frag["script_type"] == "subscript":
            elem_name = "subscript"
        else:
            elem_name = "superscript"
    elif has_different_font_from_normal(frag):
        elem_name = "emphasis"  # or "phrase"
    else:
        elem_name = "phrase"
    
    # Create inline element
    inline_elem = ET.SubElement(para_elem, elem_name, {
        "font": frag.get("font", ""),
        "size": frag.get("size", ""),
    })
    inline_elem.text = frag.get("text", "")
```

## Fix 2: Aggressive Para Grouping - Add Vertical Gap Detection

### Problem

Current code (`group_fragments_into_paragraphs`) only checks:
- Same baseline → merge (same line)
- Different baseline → DON'T merge

This causes multiple paragraphs to be grouped into one `<para>` element.

### Solution

Add vertical gap detection:
- Small gap (<= 3px) → continue paragraph
- Medium gap (3-18px) → new paragraph
- Large gap (>18px) → new paragraph with potential new element (list, blockquote, etc.)

### Implementation

**File: `pdf_to_unified_xml.py`** - function `group_fragments_into_paragraphs`

```python
def group_fragments_into_paragraphs(
    fragments: List[Dict[str, Any]],
    typical_line_height: float,
    page_num: int = 0,
    debug: bool = False,
    page_width: float = None,
) -> List[List[Dict[str, Any]]]:
    """
    Group consecutive fragments into paragraphs with vertical gap detection.
    """
    if not fragments:
        return []

    paragraphs = []
    current_paragraph = [fragments[0]]
    
    # Threshold for new paragraph (1.5x typical line height)
    paragraph_gap_threshold = typical_line_height * 1.5

    for i in range(1, len(fragments)):
        prev_fragment = fragments[i - 1]
        curr_fragment = fragments[i]
        
        # Check vertical gap
        prev_bottom = prev_fragment["top"] + prev_fragment["height"]
        curr_top = curr_fragment["top"]
        vertical_gap = curr_top - prev_bottom
        
        # Decision logic
        should_start_new_para = False
        
        # 1. Large vertical gap → always new paragraph
        if vertical_gap > paragraph_gap_threshold:
            should_start_new_para = True
        
        # 2. Different column or reading block → new paragraph
        elif (prev_fragment["col_id"] != curr_fragment["col_id"] or
              prev_fragment["reading_order_block"] != curr_fragment["reading_order_block"]):
            should_start_new_para = True
        
        # 3. Different baseline but small gap → check if same line
        elif not should_merge_fragments(prev_fragment, curr_fragment):
            # Different line, check vertical gap
            if vertical_gap > 3.0:  # More than 3px gap
                should_start_new_para = True
        
        if should_start_new_para:
            paragraphs.append(current_paragraph)
            current_paragraph = [curr_fragment]
        else:
            current_paragraph.append(curr_fragment)

    # Add the last paragraph
    if current_paragraph:
        paragraphs.append(current_paragraph)

    if debug:
        print(f"  Page {page_num}: Created {len(paragraphs)} paragraphs from {len(fragments)} fragments")

    return paragraphs
```

### RittDocDTD Nesting Rules

According to DTD, `<para>` elements:
- **CAN** contain: inline elements, text
- **CAN** be siblings with: other `<para>`, lists, tables, figures
- **CANNOT** contain: block elements like other `<para>`, `<section>`, etc.

So our approach:
- Each paragraph → one `<para>` element
- Multiple paragraphs → multiple sibling `<para>` elements
- This is DTD-compliant

## Fix 3: Image/Table Page-to-Chapter Reference Mapping

### Problem

1. Images created as: `page5_img1.png`, `page5_img2.png`, etc.
2. Tables referenced with page numbers in MultiMedia.xml
3. When creating chapter XMLs:
   - Pages 1-10 → Chapter 1
   - Pages 11-25 → Chapter 2
   - etc.
4. Image names still have page numbers but now need chapter numbers
5. Need to rename: `page5_img1.png` → `Ch0001f01.png`

### Solution Architecture

#### Phase 1: Track Page → Image Mapping (During Extraction)

**File: `Multipage_Image_Extractor.py`**

Create mapping when extracting images:

```python
# Global mapper
from reference_mapper import get_mapper

def extract_media_and_tables(pdf_path, dpi=200, out_dir=None):
    mapper = get_mapper()
    
    for page_no in range(doc.page_count):
        img_counter = 0
        for rect in image_rects:
            img_counter += 1
            filename = f"page{page_no}_img{img_counter}.png"
            
            # Register in mapper
            mapper.add_resource(
                original_path=filename,
                intermediate_name=filename,
                resource_type="image",
                first_seen_in=f"page_{page_no}",
                page_number=page_no,
                image_number_in_page=img_counter,
            )
```

#### Phase 2: Map Pages to Chapters (During Packaging)

**File: `package.py`** - in chapter extraction

```python
def extract_chapters(...):
    mapper = get_mapper()
    
    for chapter_elem in chapter_elements:
        chapter_id = generate_chapter_id(chapter_elem)
        
        # Find which pages are in this chapter
        page_ids = get_page_ids_in_chapter(chapter_elem)
        
        # Register chapter
        for page_id in page_ids:
            mapper.register_chapter(f"page_{page_id}", chapter_id)
```

#### Phase 3: Rename Images Based on Chapter (During Packaging)

**File: `package.py`** - when copying media files

```python
def copy_media_to_package(zip_handle, media_fetcher):
    mapper = get_mapper()
    
    for original_path, ref in mapper.resources.items():
        if ref.resource_type != "image":
            continue
        
        # Get chapter for this image's page
        page_id = ref.first_seen_in  # "page_5"
        chapter_id = mapper.get_chapter_id(page_id)
        
        if chapter_id:
            # Generate new name: Ch0001f01.png
            img_number = ref.image_number_in_chapter or 1
            new_filename = f"{chapter_id}f{img_number:02d}.png"
            
            mapper.update_final_name(original_path, new_filename)
            
            # Copy file with new name
            copy_and_rename_media(original_path, new_filename, zip_handle)
```

#### Phase 4: Update References in Chapter XMLs

**File: `package.py`** - when writing chapter XML

```python
def update_image_references_in_chapter(chapter_elem, chapter_id):
    mapper = get_mapper()
    
    for imageobject in chapter_elem.findall(".//imageobject"):
        imagedata = imageobject.find("imagedata")
        if imagedata is not None:
            old_fileref = imagedata.get("fileref", "")
            
            # Look up new filename in mapper
            new_filename = mapper.get_final_name(old_fileref)
            
            if new_filename:
                imagedata.set("fileref", new_filename)
```

### Detailed Implementation Steps

#### Step 1: Enhance `Multipage_Image_Extractor.py`

```python
# At the top
from reference_mapper import get_mapper

# In extract_media_and_tables function
def extract_media_and_tables(pdf_path, dpi=200, out_dir=None):
    mapper = get_mapper()
    
    # ... existing code ...
    
    for page_no in range(1, doc.page_count + 1):
        # ... existing image extraction code ...
        
        img_counter += 1
        filename = f"page{page_no}_img{img_counter}.png"
        out_path = os.path.join(media_dir, filename)
        
        # Register in reference mapper
        mapper.add_resource(
            original_path=filename,
            intermediate_name=filename,
            resource_type="image",
            first_seen_in=f"page_{page_no}",
            page_number=page_no,
            image_number_in_page=img_counter,
            width=int(rect.width),
            height=int(rect.height),
            is_raster=True,
        )
```

#### Step 2: Track Page IDs in Unified XML

**File: `pdf_to_unified_xml.py`**

Already done! We have:
```python
page_attrs["id"] = f"page_{page_number_id}"
```

#### Step 3: Map Pages to Chapters in Package.py

**File: `package.py`** - in `extract_chapters_from_book` or similar

```python
def package_docbook(...):
    mapper = get_mapper()
    
    # Extract chapters
    for chapter in chapters:
        chapter_id = chapter.get("id", f"Ch{idx:04d}")
        
        # Find all page references in this chapter
        for page_ref in chapter.findall(".//page[@id]"):
            page_id = page_ref.get("id")  # e.g., "page_5"
            mapper.register_chapter(page_id, chapter_id)
```

#### Step 4: Rename Images and Update References

**File: `package.py`** - in media copying function

```python
def process_images_for_chapters(zip_file, media_dir, mapper):
    """
    Rename images based on chapter assignment and update references.
    """
    # Group images by chapter
    images_by_chapter = defaultdict(list)
    
    for original_path, ref in mapper.resources.items():
        if ref.resource_type != "image":
            continue
        
        page_number = ref.get_metadata("page_number")
        chapter_id = mapper.get_chapter_id(f"page_{page_number}")
        
        if chapter_id:
            images_by_chapter[chapter_id].append(ref)
    
    # Rename images within each chapter
    for chapter_id, images in images_by_chapter.items():
        for idx, ref in enumerate(images, start=1):
            # New filename: Ch0001f01.png
            ext = Path(ref.intermediate_name).suffix
            new_filename = f"{chapter_id}f{idx:02d}{ext}"
            
            # Update mapper
            mapper.update_final_name(ref.original_path, new_filename)
            
            # Copy and rename file
            old_path = media_dir / ref.intermediate_name
            if old_path.exists():
                with open(old_path, 'rb') as f:
                    zip_file.writestr(f"MultiMedia/{new_filename}", f.read())
```

### Testing Strategy

1. **Extract images with mapping**
   ```bash
   python Multipage_Image_Extractor.py test.pdf
   # Check that mapper has page → image mappings
   ```

2. **Package and verify renaming**
   ```bash
   python package.py test_unified.xml
   # Check that images are renamed correctly
   # Verify chapter XMLs reference correct filenames
   ```

3. **Validate references**
   ```python
   mapper = get_mapper()
   is_valid, errors = mapper.validate(output_dir)
   print(mapper.generate_report())
   ```

## Implementation Order

### Priority 1: Para Grouping Fix (EASIEST, HIGH IMPACT)
- Modify `group_fragments_into_paragraphs()` in `pdf_to_unified_xml.py`
- Add vertical gap detection
- Test with sample PDF

### Priority 2: Image Reference Mapping (CRITICAL)
- Enhance `Multipage_Image_Extractor.py` to register images
- Modify `package.py` to map pages to chapters
- Implement image renaming logic
- Update references in chapter XMLs

### Priority 3: Fragment Tracking (COMPLEX, MEDIUM IMPACT)
- Modify `merge_inline_fragments_in_row()` to track fragments
- Modify `merge_script_with_parent()` to track fragments
- Modify `create_unified_xml()` to output inline elements
- Use `<phrase>`, `<emphasis>`, `<subscript>`, `<superscript>`

## Files to Modify

| File | Function | Change | Priority |
|------|----------|--------|----------|
| `pdf_to_unified_xml.py` | `group_fragments_into_paragraphs()` | Add vertical gap detection | 1 |
| `Multipage_Image_Extractor.py` | `extract_media_and_tables()` | Register images in mapper | 2 |
| `package.py` | `package_docbook()` | Map pages to chapters | 2 |
| `package.py` | Media copying functions | Rename images, update refs | 2 |
| `pdf_to_excel_columns.py` | `merge_inline_fragments_in_row()` | Track original fragments | 3 |
| `pdf_to_excel_columns.py` | `merge_script_with_parent()` | Track original fragments | 3 |
| `pdf_to_unified_xml.py` | `create_unified_xml()` | Output inline elements | 3 |

## Next Steps

1. ✅ Review this plan
2. ⬜ Implement Priority 1 (Para grouping fix)
3. ⬜ Implement Priority 2 (Image mapping)
4. ⬜ Implement Priority 3 (Fragment tracking)
5. ⬜ Test each fix independently
6. ⬜ Run full pipeline test
7. ⬜ Validate DTD compliance
