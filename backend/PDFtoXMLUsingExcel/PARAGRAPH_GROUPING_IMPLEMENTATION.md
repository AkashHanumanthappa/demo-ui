# Paragraph Grouping Implementation

## Overview

Implemented paragraph grouping in the unified XML output, particularly beneficial for ColID 0 (full-width) text elements such as titles, footnotes, and captions.

## Changes Made

### 1. Added Helper Functions (pdf_to_unified_xml.py)

#### `is_paragraph_break(prev_fragment, curr_fragment, typical_line_height)` (Lines 183-217)
Determines if a paragraph break should occur between two consecutive text fragments based on:
- **ColID change**: Different column IDs indicate different content streams
- **Reading block change**: Different blocks are always separate paragraphs
- **Vertical gap**: Gap > 1.5x typical line height indicates paragraph separation

#### `group_fragments_into_paragraphs(fragments, typical_line_height)` (Lines 220-256)
Groups consecutive text fragments into logical paragraphs by:
- Processing sorted fragments in reading order
- Detecting paragraph breaks using the helper function
- Returning a list of paragraph groups (each group is a list of fragments)

### 2. Modified XML Generation (Lines 315-369)

The `create_unified_xml()` function now:
1. **Calculates typical line height**: Uses median height of all text fragments for accurate break detection
2. **Groups fragments**: Calls `group_fragments_into_paragraphs()` to organize text
3. **Creates `<para>` elements**: Each paragraph gets:
   - `col_id` attribute (from first fragment in paragraph)
   - `reading_block` attribute (from first fragment in paragraph)
4. **Nests `<text>` elements**: Individual text fragments retain all original attributes

## New XML Structure

### Before (flat structure):
```xml
<texts>
  <text reading_order="1" col_id="0" ...>Title Line 1</text>
  <text reading_order="2" col_id="0" ...>Title Line 2</text>
  <text reading_order="3" col_id="1" ...>Column 1 text</text>
  <text reading_order="4" col_id="1" ...>Column 1 continued</text>
</texts>
```

### After (hierarchical with paragraphs):
```xml
<texts>
  <para col_id="0" reading_block="1">
    <text reading_order="1" ...>Title Line 1</text>
    <text reading_order="2" ...>Title Line 2</text>
  </para>
  <para col_id="1" reading_block="2">
    <text reading_order="3" ...>Column 1 text</text>
    <text reading_order="4" ...>Column 1 continued</text>
  </para>
</texts>
```

## Benefits

### For ColID 0 (Full-Width Text)
- **Semantic grouping**: Multi-line titles, footnotes, and captions are logically grouped
- **Easier processing**: Extract complete paragraphs with single XPath query: `//para[@col_id='0']`
- **Reduced redundancy**: ColID appears once per paragraph instead of per line

### For Regular Column Text (ColID 1, 2, 3...)
- **Better structure**: Column paragraphs are clearly delineated
- **Reading comprehension**: Paragraph boundaries make text flow obvious
- **Simplified extraction**: Process entire paragraphs as semantic units

### General Improvements
- **Standards compliance**: Follows XML best practices for document structure
- **Backward compatible**: Individual `<text>` elements retain all attributes
- **Intelligent detection**: Uses actual line height for accurate paragraph break detection

## Paragraph Break Detection

Paragraphs are separated when ANY of these conditions are met:

1. **ColID Change**:
   ```
   col_id=0 → col_id=1  (full-width to column)
   col_id=1 → col_id=2  (column 1 to column 2)
   ```

2. **Reading Block Change**:
   ```
   reading_block=1 → reading_block=2  (header block to column block)
   ```

3. **Significant Vertical Gap**:
   ```
   vertical_gap > 1.5 × typical_line_height
   ```
   This distinguishes paragraph breaks from normal line breaks within paragraphs.

## Implementation Details

### Typical Line Height Calculation
```python
line_heights = [f["height"] for f in sorted_fragments if f["height"] > 0]
typical_line_height = sorted(line_heights)[len(line_heights) // 2]  # median
```
Uses median (not mean) to avoid skewing from outliers like large headers.

### Attribute Inheritance
- `<para>` elements: Get `col_id` and `reading_block` from first fragment
- `<text>` elements: Retain all original attributes (reading_order, row_index, baseline, position, font, size, color, etc.)

## Testing Recommendations

1. **Multi-line titles**: Verify consecutive ColID 0 lines are grouped
2. **Footnotes**: Check bottom-of-page ColID 0 content forms paragraphs
3. **Column text**: Ensure column paragraphs are properly separated
4. **Mixed content**: Test pages with titles, columns, and footnotes
5. **Edge cases**: Single-line paragraphs, large vertical gaps

## XPath Query Examples

```xpath
// Get all full-width paragraphs
//para[@col_id='0']

// Get all paragraphs in reading block 1
//para[@reading_block='1']

// Get all text in column 1 paragraphs
//para[@col_id='1']//text

// Get ColID 0 paragraphs with specific font size
//para[@col_id='0']/text[@size='18']
```
