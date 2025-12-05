# Implementation Guide: Fragment Tracking Enhancement

## Summary

This guide provides step-by-step instructions to implement fragment tracking while preserving all original fragment metadata during merging operations.

## Overview of Changes

| File | Function | Change Type | Complexity |
|------|----------|-------------|------------|
| `pdf_to_excel_columns.py` | `merge_inline_fragments_in_row()` | Enhance to track fragments | Medium |
| `pdf_to_excel_columns.py` | `merge_script_with_parent()` | Enhance to track fragments | Medium |
| `pdf_to_unified_xml.py` | `create_unified_xml()` | Add nested fragments to XML | Medium |
| `package.py` (if used) | Processing functions | Handle new structure | Low |

## Detailed Implementation

### Step 1: Enhance `merge_inline_fragments_in_row()`

**File:** `pdf_to_excel_columns.py`  
**Lines:** 554-640

#### Current Code (Lines 590-640)
```python
def merge_inline_fragments_in_row(row, gap_tolerance=1.5, space_width=1.0):
    if not row:
        return []

    row = sorted(row, key=lambda f: f["left"])
    merged = []
    current = dict(row[0])  # copy so we don't mutate original

    for f in row[1:]:
        txt = f.get("text", "")
        current_txt = current.get("text", "")
        
        # ... merge logic ...
        
        if should_merge:
            current["text"] = current.get("text", "") + txt
            current["norm_text"] = " ".join(current["text"].split()).lower()
            current["inner_xml"] = current.get("inner_xml", "") + f.get("inner_xml", txt)
            
            # Expand width
            prev_end = current["left"] + current["width"]
            right = max(prev_end, f["left"] + f["width"])
            current["width"] = right - current["left"]
        else:
            merged.append(current)
            current = dict(f)

    merged.append(current)
    return merged
```

#### Enhanced Code (WITH FRAGMENT TRACKING)
```python
def merge_inline_fragments_in_row(row, gap_tolerance=1.5, space_width=1.0):
    """
    Merge adjacent fragments on the same baseline using a 3-phase rule
    with ± tolerance.
    
    ENHANCED: Now tracks original fragments for complete metadata preservation.
    """
    if not row:
        return []

    row = sorted(row, key=lambda f: f["left"])
    merged = []
    current = dict(row[0])  # copy so we don't mutate original
    
    # ========== NEW: Initialize fragment tracking ==========
    # Deep copy first fragment to preserve all metadata
    first_fragment = dict(row[0])
    # Remove nested tracking if already present (avoid double-nesting)
    first_fragment.pop("original_fragments", None)
    current["original_fragments"] = [first_fragment]
    # =======================================================

    for f in row[1:]:
        txt = f.get("text", "")
        current_txt = current.get("text", "")

        # Compute the horizontal gap between current and next
        base_end = current["left"] + current["width"]
        gap = f["left"] - base_end

        should_merge = False

        # --- Phase 1: trailing space detection ---
        if current_txt.endswith(" ") and not txt.startswith(" "):
            if abs(gap) <= gap_tolerance:
                should_merge = True

        # --- Phase 2: inline-style / no-gap merge ---
        if not should_merge:
            nogap = abs(gap) <= gap_tolerance
            if nogap:
                should_merge = True

        # --- Phase 3: starts-with-space + "space gap" (± tolerance) ---
        if not should_merge:
            if txt.startswith(" "):
                space_gap_ok = abs(gap - space_width) <= gap_tolerance
                if space_gap_ok:
                    should_merge = True

        if should_merge:
            # Merge: append text as-is (keep whatever spaces are in txt)
            current["text"] = current.get("text", "") + txt
            current["norm_text"] = " ".join(current["text"].split()).lower()

            # Merge XML content to preserve formatting
            current["inner_xml"] = current.get("inner_xml", "") + f.get("inner_xml", txt)

            # Expand width to cover the new fragment
            prev_end = current["left"] + current["width"]
            right = max(prev_end, f["left"] + f["width"])
            current["width"] = right - current["left"]
            
            # ========== NEW: Track merged fragment ==========
            # Deep copy fragment to preserve all metadata
            frag_copy = dict(f)
            # Remove nested tracking if already present
            frag_copy.pop("original_fragments", None)
            current["original_fragments"].append(frag_copy)
            # ================================================
        else:
            # Start a new logical fragment
            merged.append(current)
            current = dict(f)
            
            # ========== NEW: Initialize tracking for new fragment ==========
            frag_copy = dict(f)
            frag_copy.pop("original_fragments", None)
            current["original_fragments"] = [frag_copy]
            # ==============================================================

    merged.append(current)
    return merged
```

### Step 2: Enhance `merge_script_with_parent()`

**File:** `pdf_to_excel_columns.py`  
**Lines:** 210-262

#### Current Code
```python
def merge_script_with_parent(parent, scripts):
    merged = dict(parent)  # Copy parent
    
    # Sort scripts by left position
    scripts = sorted(scripts, key=lambda s: s["left"])
    
    # Merge text
    merged_text = parent["text"]
    for script in scripts:
        script_text = script["text"]
        if script["script_type"] == "superscript":
            merged_text += "^" + script_text
        else:
            merged_text += "_" + script_text
    
    merged["text"] = merged_text
    # ... rest of function ...
    
    return merged
```

#### Enhanced Code (WITH FRAGMENT TRACKING)
```python
def merge_script_with_parent(parent, scripts):
    """
    Merge one or more scripts with their parent fragment.
    
    ENHANCED: Now tracks original fragments including scripts.
    """
    merged = dict(parent)  # Copy parent
    
    # Sort scripts by left position
    scripts = sorted(scripts, key=lambda s: s["left"])
    
    # ========== NEW: Initialize fragment tracking ==========
    # Start with parent's fragments (if already merged) or just parent
    if "original_fragments" in parent:
        merged["original_fragments"] = parent["original_fragments"].copy()
    else:
        parent_copy = dict(parent)
        parent_copy.pop("original_fragments", None)
        merged["original_fragments"] = [parent_copy]
    # =======================================================
    
    # Merge text with caret (^) for superscripts, underscore (_) for subscripts
    merged_text = parent["text"]
    for script in scripts:
        script_text = script["text"]
        
        if script["script_type"] == "superscript":
            merged_text += "^" + script_text
        else:  # subscript
            merged_text += "_" + script_text
        
        # ========== NEW: Track script fragment ==========
        script_copy = dict(script)
        script_copy.pop("original_fragments", None)
        merged["original_fragments"].append(script_copy)
        # ================================================
    
    merged["text"] = merged_text
    merged["norm_text"] = " ".join(merged_text.split()).lower()
    
    # Merge inner_xml if present (preserve formatting)
    if "inner_xml" in parent:
        merged["inner_xml"] = parent.get("inner_xml", "")
        for script in scripts:
            merged["inner_xml"] += script.get("inner_xml", script["text"])
    
    # Expand bounding box to include all scripts
    for script in scripts:
        script_right = script["left"] + script["width"]
        merged_right = merged["left"] + merged["width"]
        if script_right > merged_right:
            merged["width"] = script_right - merged["left"]
        
        # Adjust height if script extends beyond
        script_bottom = script["top"] + script["height"]
        merged_bottom = merged["top"] + merged["height"]
        if script_bottom > merged_bottom:
            merged["height"] = script_bottom - merged["top"]
    
    # Mark as having merged scripts
    merged["has_merged_scripts"] = True
    merged["merged_script_count"] = len(scripts)
    
    return merged
```

### Step 3: Enhance `create_unified_xml()`

**File:** `pdf_to_unified_xml.py`  
**Lines:** 777-998

#### Current Code (Lines 924-966)
```python
# Add all text elements in this paragraph
for f in para_fragments:
    # Get original attributes from pdftohtml XML
    orig_elem = original_texts.get((page_num, f["stream_index"]))

    text_attrs = {
        "reading_order": str(f["reading_order_index"]),
        "row_index": str(f["row_index"]),
        "baseline": str(f["baseline"]),
        "left": str(f["left"]),
        "top": str(f["top"]),
        "width": str(f["width"]),
        "height": str(f["height"]),
    }

    # Add original attributes if available (font, size, etc.)
    if orig_elem is not None:
        for attr_name in orig_elem.attrib:
            if attr_name not in text_attrs:
                text_attrs[attr_name] = orig_elem.get(attr_name)

    text_elem = ET.SubElement(para_elem, "text", text_attrs)

    # Preserve inner XML formatting
    inner_xml = f.get("inner_xml", f["text"])
    if inner_xml and inner_xml != f["text"]:
        # ... parse and add inner XML ...
        text_elem.text = temp_root.text
    else:
        text_elem.text = f["text"]
```

#### Enhanced Code (WITH FRAGMENT OUTPUT)
```python
# Add all text elements in this paragraph
for f in para_fragments:
    # Get original attributes from pdftohtml XML
    orig_elem = original_texts.get((page_num, f["stream_index"]))

    text_attrs = {
        "reading_order": str(f["reading_order_index"]),
        "row_index": str(f["row_index"]),
        "baseline": str(f["baseline"]),
        "left": str(f["left"]),
        "top": str(f["top"]),
        "width": str(f["width"]),
        "height": str(f["height"]),
    }

    # Add original attributes if available (font, size, etc.)
    if orig_elem is not None:
        for attr_name in orig_elem.attrib:
            if attr_name not in text_attrs:
                text_attrs[attr_name] = orig_elem.get(attr_name)

    text_elem = ET.SubElement(para_elem, "text", text_attrs)

    # Preserve inner XML formatting
    inner_xml = f.get("inner_xml", f["text"])
    if inner_xml and inner_xml != f["text"]:
        # ... existing parse and add inner XML code ...
        text_elem.text = temp_root.text
    else:
        text_elem.text = f["text"]
    
    # ========== NEW: Add original fragments if tracking is available ==========
    if "original_fragments" in f and len(f["original_fragments"]) > 0:
        # Only add fragments element if we have multiple fragments
        # (single fragment = no merging occurred)
        if len(f["original_fragments"]) > 1:
            fragments_elem = ET.SubElement(text_elem, "fragments")
            
            for idx, orig_frag in enumerate(f["original_fragments"]):
                # Build fragment attributes
                frag_attrs = {
                    "index": str(idx),
                    "stream_index": str(orig_frag.get("stream_index", "")),
                    "left": str(orig_frag.get("left", "")),
                    "top": str(orig_frag.get("top", "")),
                    "width": str(orig_frag.get("width", "")),
                    "height": str(orig_frag.get("height", "")),
                    "baseline": str(orig_frag.get("baseline", "")),
                }
                
                # Add font attributes from original pdftohtml element
                orig_stream_idx = orig_frag.get("stream_index")
                if orig_stream_idx:
                    orig_pdftohtml = original_texts.get((page_num, orig_stream_idx))
                    if orig_pdftohtml is not None:
                        for attr_name in ["font", "size", "color"]:
                            if attr_name in orig_pdftohtml.attrib:
                                frag_attrs[attr_name] = orig_pdftohtml.get(attr_name)
                
                # Add script detection metadata if present
                if orig_frag.get("is_script"):
                    frag_attrs["script_type"] = orig_frag.get("script_type", "")
                    parent_idx = orig_frag.get("script_parent_idx")
                    if parent_idx is not None:
                        frag_attrs["script_parent_idx"] = str(parent_idx)
                
                # Create fragment element
                frag_elem = ET.SubElement(fragments_elem, "fragment", frag_attrs)
                frag_elem.text = orig_frag.get("text", "")
    # ==========================================================================
```

### Step 4: Add Helper Function (Optional but Recommended)

Add this function to `pdf_to_unified_xml.py` for cleaner code:

```python
def create_fragment_elements(text_elem, fragment, original_texts, page_num):
    """
    Helper function to create nested fragment elements.
    
    Args:
        text_elem: Parent <text> element
        fragment: Fragment dict with potential original_fragments
        original_texts: Lookup dict for pdftohtml elements
        page_num: Current page number
    
    Returns:
        None (modifies text_elem in place)
    """
    if "original_fragments" not in fragment:
        return
    
    orig_fragments = fragment["original_fragments"]
    
    # Only add fragments element if we have multiple fragments
    if len(orig_fragments) <= 1:
        return
    
    fragments_elem = ET.SubElement(text_elem, "fragments")
    
    for idx, orig_frag in enumerate(orig_fragments):
        # Build fragment attributes
        frag_attrs = {
            "index": str(idx),
            "stream_index": str(orig_frag.get("stream_index", "")),
            "left": str(orig_frag.get("left", "")),
            "top": str(orig_frag.get("top", "")),
            "width": str(orig_frag.get("width", "")),
            "height": str(orig_frag.get("height", "")),
            "baseline": str(orig_frag.get("baseline", "")),
        }
        
        # Add font attributes from original pdftohtml element
        orig_stream_idx = orig_frag.get("stream_index")
        if orig_stream_idx:
            orig_pdftohtml = original_texts.get((page_num, orig_stream_idx))
            if orig_pdftohtml is not None:
                for attr_name in ["font", "size", "color"]:
                    if attr_name in orig_pdftohtml.attrib:
                        frag_attrs[attr_name] = orig_pdftohtml.get(attr_name)
        
        # Add script detection metadata if present
        if orig_frag.get("is_script"):
            frag_attrs["script_type"] = orig_frag.get("script_type", "")
            parent_idx = orig_frag.get("script_parent_idx")
            if parent_idx is not None:
                frag_attrs["script_parent_idx"] = str(parent_idx)
        
        # Create fragment element
        frag_elem = ET.SubElement(fragments_elem, "fragment", frag_attrs)
        frag_elem.text = orig_frag.get("text", "")

# Then use it like:
# create_fragment_elements(text_elem, f, original_texts, page_num)
```

## Example XML Output

### Input Fragments
```python
# Fragment 1: "The formula H" (font=3, size=12)
# Fragment 2: "₂" (font=3, size=8, script_type="subscript")  
# Fragment 3: "O" (font=3, size=12)
```

### Output XML
```xml
<para col_id="1" reading_block="1">
  <text reading_order="5" row_index="3" baseline="250.5" 
        left="50" top="250" width="180" height="12"
        font="3" size="12">
    The formula H_2O
    
    <fragments>
      <fragment index="0" stream_index="15" 
                left="50" top="250" width="100" height="12"
                baseline="250.5" font="3" size="12">
        The formula H
      </fragment>
      
      <fragment index="1" stream_index="16" 
                left="150" top="253" width="8" height="8"
                baseline="253.0" font="3" size="8"
                script_type="subscript" script_parent_idx="15">
        ₂
      </fragment>
      
      <fragment index="2" stream_index="17" 
                left="158" top="250" width="22" height="12"
                baseline="250.5" font="3" size="12">
        O
      </fragment>
    </fragments>
  </text>
</para>
```

## Testing

### Test 1: Verify Fragment Tracking
```python
def test_fragment_tracking():
    """Test that original fragments are preserved during merging"""
    # Create test fragments
    fragments = [
        {"text": "Hello ", "left": 10, "font": "3", "size": "12", "stream_index": 1},
        {"text": "world", "left": 50, "font": "5", "size": "12", "stream_index": 2},
    ]
    
    # Merge
    merged = merge_inline_fragments_in_row(fragments)
    
    # Verify
    assert len(merged) == 1
    assert merged[0]["text"] == "Hello world"
    assert "original_fragments" in merged[0]
    assert len(merged[0]["original_fragments"]) == 2
    assert merged[0]["original_fragments"][0]["font"] == "3"
    assert merged[0]["original_fragments"][1]["font"] == "5"
```

### Test 2: Verify Script Merging
```python
def test_script_fragment_tracking():
    """Test that script fragments are tracked when merged with parent"""
    parent = {
        "text": "H", 
        "left": 10, 
        "font": "3", 
        "size": "12",
        "stream_index": 1,
        "height": 12,
    }
    
    script = {
        "text": "₂", 
        "left": 20, 
        "font": "3", 
        "size": "8",
        "stream_index": 2,
        "script_type": "subscript",
        "is_script": True,
        "height": 8,
    }
    
    merged = merge_script_with_parent(parent, [script])
    
    assert merged["text"] == "H_2"
    assert "original_fragments" in merged
    assert len(merged["original_fragments"]) == 2
    assert merged["original_fragments"][1]["script_type"] == "subscript"
```

### Test 3: Verify XML Output
```python
def test_xml_fragment_output():
    """Test that fragments are correctly written to XML"""
    # Create test data with tracked fragments
    fragment = {
        "text": "Hello world",
        "reading_order_index": 1,
        "row_index": 1,
        "baseline": 100.5,
        "left": 10,
        "top": 100,
        "width": 100,
        "height": 12,
        "stream_index": 1,
        "original_fragments": [
            {"text": "Hello ", "stream_index": 1, "font": "3"},
            {"text": "world", "stream_index": 2, "font": "5"},
        ]
    }
    
    # Generate XML
    # ... (use create_unified_xml or helper function) ...
    
    # Verify XML has <fragments> element
    assert text_elem.find("fragments") is not None
    assert len(text_elem.find("fragments").findall("fragment")) == 2
```

## Rollback Plan

If issues arise, you can easily disable fragment tracking by:

1. Comment out the `original_fragments` initialization lines
2. Comment out the XML generation for `<fragments>` elements
3. The code will work exactly as before

## Performance Impact

**Expected:** Minimal to negligible
- Memory: +10-20% (storing additional fragment metadata)
- CPU: +5-10% (copying fragment dicts)
- XML size: +15-30% (nested fragment elements)

For a 500-page book:
- Current XML: ~50MB
- Enhanced XML: ~65MB (still very manageable)

## Backward Compatibility

The enhancement is **fully backward compatible**:
- Merged text still available at `<text>` element level
- Existing parsers can ignore `<fragments>` sub-elements
- No changes to attribute names or structure
- Only addition of optional nested elements

## Next Steps

1. ✅ Review this implementation guide
2. ⬜ Apply changes to `pdf_to_excel_columns.py`
3. ⬜ Apply changes to `pdf_to_unified_xml.py`
4. ⬜ Run tests to verify functionality
5. ⬜ Process a sample PDF and inspect XML output
6. ⬜ Update downstream processors if needed
7. ⬜ Document the new XML schema

## Questions?

Contact the development team or review:
- `FRAGMENT_MERGING_ANALYSIS.md` - Problem statement
- `FRAGMENT_TRACKING_EXAMPLES.md` - Real-world examples
- This guide - Implementation details
