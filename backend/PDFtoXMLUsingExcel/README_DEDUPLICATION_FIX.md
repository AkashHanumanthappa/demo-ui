# Raster-Vector Deduplication Fix - Complete Guide

## Quick Start

**Your issue is now fixed!** The system automatically detects and skips vector regions that contain already-captured raster images.

No configuration needed - just run your pipeline as usual:

```bash
python3 pdf_to_unified_xml.py your_file.pdf --full-pipeline
```

---

## Table of Contents

1. [Problem Overview](#problem-overview)
2. [Solution](#solution)
3. [How It Works](#how-it-works)
4. [Testing](#testing)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [Technical Details](#technical-details)

---

## Problem Overview

### What Was Happening

When processing PDFs with complex figures (e.g., "Figure 4" with two side-by-side diagrams), the system captured content twice:

```
INPUT: PDF page with Figure 4
┌─────────────────────────────────────┐
│ Figure 4. Radiofrequency (RF)...   │
│ ┌────────────┐    ┌────────────┐   │
│ │ Diagram A  │    │ Diagram B  │   │
│ └────────────┘    └────────────┘   │
└─────────────────────────────────────┘

OUTPUT (Before Fix):
├─ page5_img1.png ← Raster capture of Diagram A ✓
├─ page5_img2.png ← Raster capture of Diagram B ✓
└─ page5_vector1.png ← Vector capture of ENTIRE block ✗ DUPLICATE!
   (includes Figure label + both diagrams)
```

### Why It Happened

The overlap detection used **IoU (Intersection over Union)** which doesn't work well when comparing regions of very different sizes:

- Large vector region (e.g., 800×400 px) containing small rasters (e.g., 300×300 px each)
- IoU = 28% < 30% threshold → Vector NOT skipped
- Result: Duplicate capture

---

## Solution

### What Changed

Modified the overlap detection in `Multipage_Image_Extractor.py` to use **raster containment ratio** instead of IoU:

**New Logic:**
```
If ANY raster image has >20% of its area contained within a vector region:
  → Skip the vector (already captured as raster)
Otherwise:
  → Keep the vector (legitimate diagram)
```

This is **size-independent** and correctly handles cases where large vector regions contain smaller raster images.

### Result

```
OUTPUT (After Fix):
├─ page5_img1.png ← Raster capture of Diagram A ✓
└─ page5_img2.png ← Raster capture of Diagram B ✓

No page5_vector1.png - correctly skipped! ✓
```

---

## How It Works

### Processing Flow

```
1. RASTER EXTRACTION (First Pass)
   ├─ Scan page for embedded raster images
   ├─ Extract and save each raster image
   └─ Track bounding boxes: [rect1, rect2, ...]
           ↓
2. VECTOR EXTRACTION (Second Pass)
   ├─ Scan page for vector drawings
   ├─ For each vector region found:
   │  ├─ Check: Does it overlap with any raster?
   │  │  ├─ Calculate: intersection_area / raster_area
   │  │  ├─ If ratio > 20% → SKIP (duplicate)
   │  │  └─ If ratio ≤ 20% → Continue checking...
   │  ├─ Check: Does it have Figure/Table keywords?
   │  ├─ Check: Does it contain complex shapes (curves, etc.)?
   │  └─ Decision: Keep or skip based on checks
   └─ Extract and save remaining vectors
           ↓
3. FINAL OUTPUT
   └─ No duplicate captures! ✓
```

### Overlap Detection Algorithm

```python
# For each vector region detected:
for each raster_rect in page_raster_rects:
    if vector_rect.intersects(raster_rect):
        # Calculate intersection
        x_overlap = min(vector.x2, raster.x2) - max(vector.x1, raster.x1)
        y_overlap = min(vector.y2, raster.y2) - max(vector.y1, raster.y1)
        intersection_area = x_overlap * y_overlap
        
        # Calculate containment ratio
        raster_area = raster_rect.width * raster_rect.height
        overlap_ratio = intersection_area / raster_area
        
        # Decision
        if overlap_ratio > 0.2:  # 20% threshold
            skip_vector = True
            break
```

---

## Testing

### Automated Test Suite

Run the test suite to verify the fix:

```bash
python3 test_raster_vector_overlap.py
```

**Expected Output:**
```
======================================================================
RASTER-VECTOR OVERLAP DETECTION TESTS
======================================================================

======================================================================
TEST: Figure with two side-by-side images + label
======================================================================
...
Decision: SKIP vector (✓ correct)
✓ TEST PASSED

======================================================================
TEST: Pure vector diagram (no raster overlap)
======================================================================
...
Decision: KEEP vector (✓ correct)
✓ TEST PASSED

======================================================================
✓ ALL TESTS PASSED
======================================================================
```

### Test Your PDF

```bash
# Process your PDF
python3 pdf_to_unified_xml.py your_file.pdf --full-pipeline

# Check the output folder
ls -lh your_file_MultiMedia/

# Should see:
# - Raster images (page*_img*.png)
# - Vector diagrams (page*_vector*.png) - only legitimate ones
# - No duplicates!
```

### Verify XML Output

```bash
# Inspect the media XML
cat your_file_MultiMedia.xml | grep '<media'

# Should see:
# <media id="p5_img1" type="raster" ...>  ✓ Raster 1
# <media id="p5_img2" type="raster" ...>  ✓ Raster 2
# (No duplicate vector covering same area)
```

---

## Configuration

### Default Settings

The fix works out-of-the-box with sensible defaults:

- **Overlap threshold:** 20% (0.2)
- **Automatic:** No configuration required
- **Debug logging:** Disabled (can be enabled)

### Adjust Overlap Threshold

If you need different behavior, edit line 663 in `Multipage_Image_Extractor.py`:

```python
if raster_area > 0 and (intersection_area / raster_area) > 0.2:
                                                            ↑
                                                    Change this value
```

**Recommended Values:**

| Threshold | Behavior | Best For |
|-----------|----------|----------|
| **0.2** (20%) | **Balanced** (recommended) | Most PDFs with figures |
| 0.1 (10%) | Aggressive deduplication | Heavy duplication problems |
| 0.5 (50%) | Conservative | Complex layouts with intentional overlap |
| 0.8 (80%) | Very conservative | Edge cases only |

### Enable Debug Logging

To see why vectors are skipped, uncomment line 670 in `Multipage_Image_Extractor.py`:

```python
if skip_vector:
    print(f"    Page {page_no}: Skipping vector region - {skip_reason}")  # ← Uncomment
    continue
```

**Example Output:**
```
Page 5: Skipping vector region - contains raster image #1 (100.0% overlap)
Page 7: Skipping vector region - contains raster image #2 (85.3% overlap)
```

---

## Troubleshooting

### Issue: Still Seeing Duplicates

**Possible Causes:**

1. **Threshold too high** - Lower the threshold (try 0.1 instead of 0.2)
2. **Partial overlap** - Rasters only partially overlap vector region
3. **Different types** - Check if both items have figure keywords

**Debug Steps:**
```bash
# Enable debug logging (see above)
# Process your PDF again
python3 pdf_to_unified_xml.py your_file.pdf --full-pipeline

# Look for skip messages in output
# If not skipping when it should, lower threshold
```

### Issue: Missing Legitimate Vectors

**Possible Causes:**

1. **Threshold too low** - Raise the threshold (try 0.5 instead of 0.2)
2. **Incidental overlap** - Vector diagram has small raster icon nearby

**Debug Steps:**
```bash
# Enable debug logging
# Check which vectors are being skipped
# If skipping too aggressively, raise threshold
```

### Issue: Complex Figures Not Handled

Some complex multi-panel figures may need manual review:

1. Check if all panels are being captured
2. Verify XML structure has correct associations
3. Adjust threshold if needed for your specific PDF layout

---

## Technical Details

### Files Modified

1. **`Multipage_Image_Extractor.py`** (lines 646-671)
   - Added improved overlap detection logic
   - Calculates raster containment ratio
   - Skips vectors containing already-captured rasters

### Algorithm Comparison

**Before (IoU-based):**
```python
# Problem: Size-dependent
iou = intersection / (area1 + area2 - intersection)
if iou > 0.3:
    skip_vector = True

# Example: Large vector + small raster
# iou = 90k / (320k + 90k - 90k) = 0.28 < 0.3
# Result: NOT SKIPPED (wrong!)
```

**After (Containment-based):**
```python
# Solution: Size-independent
overlap_ratio = intersection / raster_area
if overlap_ratio > 0.2:
    skip_vector = True

# Example: Large vector + small raster
# overlap_ratio = 90k / 90k = 1.0 > 0.2
# Result: SKIPPED (correct!)
```

### Performance Impact

- **CPU:** Negligible - simple arithmetic operations
- **Memory:** No additional memory usage
- **I/O:** Reduced - fewer duplicate images written
- **Storage:** Improved - eliminates duplicate files

### Edge Cases Handled

1. ✓ Figure with multiple side-by-side images + label
2. ✓ Figure with stacked images + caption
3. ✓ Large composite figures spanning multiple columns
4. ✓ Pure vector diagrams (no rasters) - correctly preserved
5. ✓ Mixed content pages with separate rasters and vectors

---

## Related Documentation

- **`SOLUTION_SUMMARY.md`** - High-level overview of the fix
- **`DEDUPLICATION_VISUAL_GUIDE.md`** - Visual diagrams and examples
- **`RASTER_VECTOR_DEDUPLICATION_FIX.md`** - Detailed technical explanation
- **`test_raster_vector_overlap.py`** - Test suite source code

---

## Summary

✅ **Problem Fixed:** Vector regions containing rasters are now correctly skipped  
✅ **Automatic:** Works out-of-the-box with no configuration  
✅ **Tested:** Comprehensive test suite verifies correct behavior  
✅ **Configurable:** Adjustable threshold for different use cases  
✅ **Backward Compatible:** No breaking changes to existing pipelines  

**Your Figure 4 scenario is now handled correctly!**

```
Before: 3 images (2 rasters + 1 duplicate vector)
After:  2 images (2 rasters only) ✓
```

---

## Questions?

If you encounter any issues or edge cases:

1. Run the test suite: `python3 test_raster_vector_overlap.py`
2. Enable debug logging (see Configuration section)
3. Adjust threshold if needed
4. Check the visual guide for similar examples

The fix is robust and should handle your use case correctly!
