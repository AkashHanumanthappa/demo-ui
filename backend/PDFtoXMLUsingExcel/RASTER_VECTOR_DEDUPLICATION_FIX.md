# Raster-Vector Duplication Fix

## Problem Description

When processing PDFs with figures that contain multiple raster images alongside labels (e.g., "Figure 4"), the system was capturing content twice:

1. **Raster extraction** correctly captured the individual images
2. **Vector extraction** then captured a large bounding box around the entire Figure block (images + label)

This resulted in duplicate image captures where the same visual content appeared in both raster and vector outputs.

### Example Case

```
Figure 4. Radiofrequency (RF)...
[Image A]  [Image B]
```

- Raster extraction: Captured Image A and Image B separately ✓
- Vector extraction: Captured large bbox around "Figure 4 + Image A + Image B" ✗ (duplicate!)

## Root Cause

The overlap detection logic used **Intersection over Union (IoU)** to check if a vector region overlaps with raster images:

```python
if any(rect_iou(rect, r_rect) > 0.3 for r_rect in raster_rects):
    continue  # Skip vector
```

**Why this failed:**
- IoU = intersection_area / (area1 + area2 - intersection_area)
- When vector region is MUCH LARGER than raster images, IoU becomes very small
- Example:
  - Vector region: 1000x400 = 400,000 sq px
  - Raster image: 300x300 = 90,000 sq px
  - IoU = 90,000 / (400,000 + 90,000 - 90,000) = 90,000 / 400,000 = 0.225 (22.5%)
  - 22.5% < 30% threshold → vector NOT skipped → duplicate!

## Solution

Changed the overlap detection to use **intersection area vs raster area** instead of IoU:

```python
# Calculate intersection area vs raster area
x_overlap = max(0, min(rect.x1, r_rect.x1) - max(rect.x0, r_rect.x0))
y_overlap = max(0, min(rect.y1, r_rect.y1) - max(rect.y0, r_rect.y0))
intersection_area = x_overlap * y_overlap
raster_area = r_rect.width * r_rect.height

# If > 20% of the raster is within this vector region, skip the vector
if raster_area > 0 and (intersection_area / raster_area) > 0.2:
    skip_vector = True
```

**Why this works:**
- Measures what percentage of the RASTER image is contained in the vector region
- Independent of vector region size
- If raster is substantially contained (>20%), the vector is redundant → skip it

### Example with new logic:
- Vector region: 1000x400 pixels
- Raster image: 300x300 pixels, fully contained
- overlap_ratio = 90,000 / 90,000 = 100%
- 100% > 20% threshold → vector SKIPPED → no duplicate! ✓

## Benefits

1. **Eliminates duplicate captures** for Figures with multiple images + labels
2. **Preserves pure vector diagrams** that don't contain raster images
3. **Size-independent detection** - works regardless of vector region size
4. **Configurable threshold** (default 20%) for fine-tuning

## Testing

Run the test suite to verify the fix:

```bash
python3 test_raster_vector_overlap.py
```

Test cases cover:
1. Figure with multiple raster images + label (should skip vector)
2. Pure vector diagram with no raster overlap (should keep vector)
3. Threshold-based edge cases

## Configuration

If you need to adjust the overlap threshold, edit line 663 in `Multipage_Image_Extractor.py`:

```python
if raster_area > 0 and (intersection_area / raster_area) > 0.2:  # Change 0.2 to desired threshold
```

Recommended values:
- **0.2 (20%)** - Default, good balance (recommended)
- **0.5 (50%)** - More conservative, may allow some duplicates
- **0.1 (10%)** - More aggressive, may skip legitimate vectors with minor overlap

## Debug Logging

To enable debug logging showing why vectors are skipped, uncomment line 670:

```python
if skip_vector:
    print(f"    Page {page_no}: Skipping vector region - {skip_reason}")
    continue
```

This will print messages like:
```
Page 5: Skipping vector region - contains raster image #1 (100.0% overlap)
```

## Files Modified

- `Multipage_Image_Extractor.py` - Lines 646-671: Improved overlap detection
- `test_raster_vector_overlap.py` - NEW: Test suite for overlap detection

## Related Issues

This fix addresses the issue where:
- Figures with side-by-side images get captured twice
- Figure captions/labels are included in vector captures
- Large vector bounding boxes encompass already-captured raster content

The solution ensures that once raster images are captured, vector extraction intelligently skips regions that would create duplicates.
