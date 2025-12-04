# Complex Drawing Shape Detection

## Overview

This implementation adds intelligent detection of complex drawing shapes in vector regions to ensure diagrams with embedded text labels are properly captured as images.

## Problem Statement

Previously, text-heavy vector regions were filtered out and not captured as images, even if they contained important diagrams with text labels. This resulted in loss of visual information for diagrams like:
- Flowcharts with text in boxes
- Circuit diagrams with component labels
- Architectural diagrams with annotations
- Process diagrams with descriptive text

## Solution

### 1. Complex Shape Detection Function

Added `has_complex_drawing_shapes(rect, drawings)` function that analyzes drawing primitives within a region to detect:

#### Complex Shapes Detected:
- **Curves** (operator 'c'): Bezier curves used for circles, ovals, arcs
- **Multiple Lines** (operator 'l'): Non-rectangular arrangements suggesting arrows, connectors, or complex shapes
- **Quads** (operator 'qu'): Non-rectangular quadrilaterals
- **Mixed Combinations**: Curves + lines (labeled diagrams)

#### Detection Thresholds:
- `min_curves = 1`: Any curve indicates a diagram
- `min_complex_lines = 3`: Three or more lines suggest complex shapes
- Combinations: curves + multiple lines, or multiple quads

### 2. Updated Vector Extraction Logic

Modified `extract_vector_blocks_for_page()` to:

1. **Check for figure keywords** (existing behavior)
2. **Check for complex drawing shapes** (new behavior)
3. **Determine if text-heavy** (existing behavior)
4. **Apply decision logic**:
   - ✅ Keep if has figure keywords
   - ✅ Keep if has complex drawing shapes (even if text-heavy)
   - ❌ Skip if text-heavy AND no keywords AND no complex shapes
   - ❌ Skip if no keywords AND no complex shapes

## Examples

### Captured Regions (Will be saved as images):

1. **Diagram with circles and text labels**
   - Has curves (circles) → `has_complex_shapes = True`
   - Even if text-heavy → Still captured ✅

2. **Flowchart with arrows and boxes**
   - Has multiple lines forming arrows → `has_complex_shapes = True`
   - Contains descriptive text → Still captured ✅

3. **Process diagram with ovals and connectors**
   - Has curves (ovals) + lines (connectors) → `has_complex_shapes = True`
   - Text labels present → Still captured ✅

### Filtered Regions (Will NOT be saved):

1. **Simple text box with border**
   - Only rectangles, no complex shapes
   - No figure keywords
   - Filtered out ❌

2. **Text paragraph with underlines**
   - Simple lines forming rectangles
   - No curves or complex shapes
   - Filtered out ❌

## Technical Details

### Drawing Operators Analyzed:
```python
'c'  : Bezier curve (circles, ovals, arcs)
'l'  : Line (can form arrows, connectors)
're' : Rectangle (simple boxes)
'qu' : Quadrilateral (non-rectangular shapes)
```

### Function Signature:
```python
def has_complex_drawing_shapes(
    rect: fitz.Rect,
    drawings: List[Dict[str, Any]],
    min_curves: int = 1,
    min_complex_lines: int = 3,
) -> bool
```

### Integration Point:
The function is called in `extract_vector_blocks_for_page()` at line 581:
```python
has_complex_shapes = has_complex_drawing_shapes(rect, drawings)
```

## Benefits

1. **Zero information loss**: Diagrams with text labels are preserved
2. **Smart filtering**: Simple text boxes without diagrams are still filtered
3. **Configurable thresholds**: Tune sensitivity via parameters
4. **Robust detection**: Multiple heuristics ensure accurate classification

## Configuration

You can adjust detection sensitivity by modifying these parameters in the `has_complex_drawing_shapes()` function:
- `min_curves`: Number of curves needed (default: 1)
- `min_complex_lines`: Number of lines suggesting complexity (default: 3)

## Testing

To test the implementation, process a PDF with diagrams containing text labels:

```bash
python3 Multipage_Image_Extractor.py your_document.pdf
```

Check the output `*_MultiMedia/` folder for captured vector images. Diagrams with circles, ovals, arrows, and text labels should now be captured correctly.
