# Fragment Tracking: Current vs. Proposed

## Example Scenario

Consider this line of text from a PDF:
```
"The formula H₂O has a subscript"
```

In the original PDF, this is split into multiple fragments:
1. Fragment A: "The formula H" (font=3, size=12, left=50, width=80)
2. Fragment B: "₂" (font=3, size=8, left=130, width=5) ← **subscript**
3. Fragment C: "O has a subscript" (font=3, size=12, left=135, width=120)

## Current Implementation

### Step 1: Script Detection (pdf_to_excel_columns.py)
The script detector identifies Fragment B as a subscript and marks it for merging.

### Step 2: Merging (merge_script_with_parent)
```python
# Fragment B is merged into Fragment A
merged["text"] = "The formula H_2"  # _2 denotes subscript
merged["font"] = "3"  # From Fragment A
merged["size"] = "12"  # From Fragment A
merged["left"] = 50
merged["width"] = 135  # Extended to cover Fragment B
```

### Step 3: Inline Merging (merge_inline_fragments_in_row)
```python
# The merged fragment is then merged with Fragment C
final["text"] = "The formula H_2O has a subscript"
final["font"] = "3"  # From Fragment A only
final["size"] = "12"  # From Fragment A only
final["left"] = 50
final["width"] = 255  # Full width
```

### Step 4: Current XML Output
```xml
<para col_id="1" reading_block="1">
  <text reading_order="1" row_index="1" baseline="100.5" 
        left="50" top="100" width="255" height="12"
        font="3" size="12">
    The formula H_2O has a subscript
  </text>
</para>
```

**PROBLEM:** We lost the information that "₂" was originally:
- A separate fragment
- Size 8 (not 12)
- At position left=130
- Identified as a subscript

## What We're Missing

### Lost Information Summary

| Property | Fragment A | Fragment B | Fragment C | Final |
|----------|-----------|------------|------------|-------|
| text | "The formula H" | "₂" | "O has a subscript" | "The formula H_2O has a subscript" |
| font | 3 | 3 | 3 | **3 (only first)** |
| size | 12 | **8** | 12 | **12 (lost size=8)** |
| left | 50 | **130** | 135 | 50 |
| width | 80 | **5** | 120 | 255 |
| Script Type | - | **"subscript"** | - | **LOST** |

## Proposed Solution: Enhanced XML Structure

### Option A: Nested Fragment Preservation (RECOMMENDED)

```xml
<para col_id="1" reading_block="1">
  <text reading_order="1" row_index="1" baseline="100.5" 
        left="50" top="100" width="255" height="12">
    <!-- Merged text content for convenience -->
    The formula H_2O has a subscript
    
    <!-- Original fragments with full metadata -->
    <fragments>
      <fragment stream_index="1" font="3" size="12" 
                left="50" top="100" width="80" height="12"
                script_type="">
        The formula H
      </fragment>
      
      <fragment stream_index="2" font="3" size="8" 
                left="130" top="103" width="5" height="8"
                script_type="subscript" script_parent="1">
        ₂
      </fragment>
      
      <fragment stream_index="3" font="3" size="12" 
                left="135" top="100" width="120" height="12"
                script_type="">
        O has a subscript
      </fragment>
    </fragments>
  </text>
</para>
```

**Advantages:**
- ✅ Preserves ALL original fragment information
- ✅ Maintains script detection metadata (script_type, script_parent)
- ✅ Allows downstream processors to access individual fonts/sizes
- ✅ Enables proper styling reconstruction
- ✅ Backward compatible (merged text still available)
- ✅ Can reconstruct original PDF structure exactly

### Option B: Compact Metadata Arrays

```xml
<para col_id="1" reading_block="1">
  <text reading_order="1" row_index="1" baseline="100.5" 
        left="50" top="100" width="255" height="12"
        merged_count="3"
        merged_stream_indices="1,2,3"
        merged_fonts="3,3,3"
        merged_sizes="12,8,12"
        merged_lefts="50,130,135"
        merged_widths="80,5,120"
        merged_script_types="none,subscript,none">
    The formula H_2O has a subscript
  </text>
</para>
```

**Advantages:**
- ✅ Compact representation
- ✅ Preserves key metadata
- ⚠️ Harder to parse and map to text segments
- ⚠️ Less intuitive structure

### Option C: Mixed Inline Format (Alternative)

```xml
<para col_id="1" reading_block="1">
  <text reading_order="1" row_index="1" baseline="100.5" 
        left="50" top="100" width="255" height="12">
    <span font="3" size="12" left="50" width="80">The formula H</span>
    <span font="3" size="8" left="130" width="5" script="sub">₂</span>
    <span font="3" size="12" left="135" width="120">O has a subscript</span>
  </text>
</para>
```

**Advantages:**
- ✅ Natural HTML-like structure
- ✅ Easy to map fonts to text segments
- ⚠️ Changes current <text> element content model
- ⚠️ May break existing parsers

## Real-World Impact Examples

### Example 1: Index Entry with Mixed Fonts

**PDF Content:**
```
"Introduction, 1–5, 23"
```

**Original Fragments:**
1. "Introduction, " (font=2, size=11) ← body text
2. "1–5, 23" (font=4, size=11) ← bold page numbers

**Current Output (WRONG):**
```xml
<text font="2" size="11">Introduction, 1–5, 23</text>
```
❌ Lost the fact that page numbers are in font=4 (bold)

**Proposed Output (CORRECT):**
```xml
<text>
  Introduction, 1–5, 23
  <fragments>
    <fragment font="2">Introduction, </fragment>
    <fragment font="4">1–5, 23</fragment>
  </fragments>
</text>
```
✅ Preserves font distinction for proper page number extraction

### Example 2: Emphasis in Body Text

**PDF Content:**
```
"This is important text"
```

**Original Fragments:**
1. "This is " (font=3, size=12) ← regular
2. "important" (font=5, size=12) ← italic
3. " text" (font=3, size=12) ← regular

**Current Output (PARTIAL):**
```xml
<text font="3" size="12">This is important text</text>
```
❌ Lost the italic emphasis on "important"

**Note:** The `inner_xml` field might preserve `<i>` tags from pdftohtml:
```python
current["inner_xml"] = "This is <i>important</i> text"
```
⚠️ This helps, but doesn't preserve font ID (needed for consistent styling)

**Proposed Output (COMPLETE):**
```xml
<text>
  This is <i>important</i> text
  <fragments>
    <fragment font="3">This is </fragment>
    <fragment font="5"><i>important</i></fragment>
    <fragment font="3"> text</fragment>
  </fragments>
</text>
```
✅ Preserves both formatting AND font ID

### Example 3: Chemical Formula

**PDF Content:**
```
"CO₂ emissions"
```

**Original Fragments:**
1. "CO" (font=3, size=12)
2. "₂" (font=3, size=8) ← subscript
3. " emissions" (font=3, size=12)

**Current Output:**
```xml
<text font="3" size="12">CO_2 emissions</text>
```
⚠️ We mark it with "_2", but lose the original size=8

**Proposed Output:**
```xml
<text>
  CO_2 emissions
  <fragments>
    <fragment font="3" size="12">CO</fragment>
    <fragment font="3" size="8" script_type="subscript">₂</fragment>
    <fragment font="3" size="12"> emissions</fragment>
  </fragments>
</text>
```
✅ Preserves subscript size for proper rendering

## Implementation Plan

### Phase 1: Enhance Fragment Tracking (pdf_to_excel_columns.py)

```python
def merge_inline_fragments_in_row(row, gap_tolerance=1.5, space_width=1.0):
    """Enhanced version that tracks original fragments"""
    if not row:
        return []
    
    row = sorted(row, key=lambda f: f["left"])
    merged = []
    current = dict(row[0])
    
    # NEW: Track original fragments
    current["original_fragments"] = [dict(row[0])]
    
    for f in row[1:]:
        # ... existing merge logic ...
        
        if should_merge:
            # Existing merge code
            current["text"] = current.get("text", "") + txt
            
            # NEW: Append to fragment list
            current["original_fragments"].append(dict(f))
        else:
            merged.append(current)
            current = dict(f)
            current["original_fragments"] = [dict(f)]
    
    merged.append(current)
    return merged
```

### Phase 2: Enhance XML Generation (pdf_to_unified_xml.py)

```python
def create_unified_xml(...):
    # ... existing code ...
    
    for f in para_fragments:
        text_elem = ET.SubElement(para_elem, "text", text_attrs)
        text_elem.text = f["text"]
        
        # NEW: Add fragments sub-element if we have tracking
        if "original_fragments" in f and len(f["original_fragments"]) > 1:
            fragments_elem = ET.SubElement(text_elem, "fragments")
            
            for orig_frag in f["original_fragments"]:
                frag_attrs = {
                    "stream_index": str(orig_frag.get("stream_index", "")),
                    "font": str(orig_frag.get("font", "")),
                    "size": str(orig_frag.get("size", "")),
                    "left": str(orig_frag.get("left", "")),
                    "top": str(orig_frag.get("top", "")),
                    "width": str(orig_frag.get("width", "")),
                    "height": str(orig_frag.get("height", "")),
                }
                
                # Add script detection metadata
                if orig_frag.get("is_script"):
                    frag_attrs["script_type"] = orig_frag.get("script_type", "")
                    frag_attrs["script_parent_idx"] = str(orig_frag.get("script_parent_idx", ""))
                
                frag_elem = ET.SubElement(fragments_elem, "fragment", frag_attrs)
                frag_elem.text = orig_frag.get("text", "")
```

### Phase 3: Update Downstream Processors

1. **font_roles_auto.py**: Read from `<fragments>` if available
2. **package.py**: Preserve `<fragments>` in final output
3. **XSLT transforms**: Handle nested fragments structure

## Testing Strategy

### Test 1: Script Detection Preservation
```python
def test_subscript_preservation():
    # Input: "H₂O" with subscript
    # Expected: Fragment tracking shows size=8 for "₂"
    assert fragments[1]["size"] == "8"
    assert fragments[1]["script_type"] == "subscript"
```

### Test 2: Mixed Font Preservation
```python
def test_mixed_fonts():
    # Input: "Hello world" where "world" is bold
    # Expected: Fragment tracking shows font=5 for "world"
    assert fragments[0]["font"] == "3"
    assert fragments[1]["font"] == "5"
```

### Test 3: Backward Compatibility
```python
def test_backward_compatibility():
    # Existing code should work with new structure
    text_content = text_elem.text
    assert text_content == "Expected merged text"
```

## Conclusion

**Your concern is absolutely valid.** The current implementation loses critical fragment-level information during merging. The proposed solution (Option A: Nested Fragment Preservation) provides the best balance of:

- ✅ Complete information preservation
- ✅ Backward compatibility
- ✅ Clear, parseable structure
- ✅ Support for downstream processing

This change would require modifications to 2-3 files but would significantly improve the quality and usefulness of the final XML output.
