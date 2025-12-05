# Visual Guide: Raster-Vector Deduplication Fix

## Before Fix: Duplicate Captures

```
PDF Page with Figure:
┌─────────────────────────────────────────────────┐
│  Figure 4. Radiofrequency (RF) energy...        │
│  ┌──────────────┐      ┌──────────────┐         │
│  │   Image A    │      │   Image B    │         │
│  │ (Diagram 1)  │      │ (Diagram 2)  │         │
│  │              │      │              │         │
│  │              │      │              │         │
│  └──────────────┘      └──────────────┘         │
└─────────────────────────────────────────────────┘

EXTRACTION RESULTS (OLD):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Raster Extraction: ✓
   ✓ page5_img1.png (Image A)
   ✓ page5_img2.png (Image B)

2. Vector Extraction: ✗ DUPLICATE!
   ✗ page5_vector1.png (ENTIRE Figure block including A + B + label)

PROBLEM:
- 3 images saved (should be 2)
- Redundant captures of same content
- Wastes storage and confuses downstream processing
```

## Why the Old Logic Failed

```
OLD OVERLAP DETECTION: IoU (Intersection over Union)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IoU = intersection_area / (area1 + area2 - intersection_area)

Example:
┌────────────────────────────────────┐ ← Vector region
│ "Figure 4..."                      │   (800 × 400 = 320,000 sq px)
│ ┌──────┐        ┌──────┐           │
│ │Raster│        │Raster│           │ ← Each raster
│ │  A   │        │  B   │           │   (300 × 300 = 90,000 sq px)
│ └──────┘        └──────┘           │
└────────────────────────────────────┘

Calculation for Raster A:
- Intersection: 90,000 sq px (raster fully inside vector)
- Union: 320,000 + 90,000 - 90,000 = 320,000 sq px
- IoU = 90,000 / 320,000 = 0.28 = 28%

Result: 28% < 30% threshold → Vector NOT SKIPPED ✗

WHY IT FAILS:
Large vector regions have low IoU even when they
completely contain the raster images!
```

## After Fix: Smart Deduplication

```
NEW OVERLAP DETECTION: Intersection / Raster Area
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overlap = intersection_area / raster_area

Same example:
┌────────────────────────────────────┐ ← Vector region
│ "Figure 4..."                      │   (800 × 400 = 320,000 sq px)
│ ┌──────┐        ┌──────┐           │
│ │Raster│        │Raster│           │ ← Each raster
│ │  A   │        │  B   │           │   (300 × 300 = 90,000 sq px)
│ └──────┘        └──────┘           │
└────────────────────────────────────┘

Calculation for Raster A:
- Intersection: 90,000 sq px
- Raster area: 90,000 sq px
- Overlap = 90,000 / 90,000 = 1.0 = 100%

Result: 100% > 20% threshold → Vector SKIPPED ✓

WHY IT WORKS:
Measures what fraction of the RASTER is contained in
the vector, independent of vector size!
```

## Extraction Flow After Fix

```
PDF PROCESSING PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: RASTER EXTRACTION
┌─────────────────────────────────┐
│ Scan page for raster images     │
│ - Found: Image A at (100,100)   │
│ - Found: Image B at (500,100)   │
│ Save: page5_img1.png ✓          │
│ Save: page5_img2.png ✓          │
│ Track locations: [A_rect, B_rect]│
└─────────────────────────────────┘
         ↓

Step 2: VECTOR EXTRACTION (with deduplication)
┌─────────────────────────────────┐
│ Scan page for vector drawings   │
│ - Found: Large region (80,50)   │
│                                 │
│ CHECK: Does it overlap rasters? │
│  → Raster A: 100% contained ✓   │
│  → SKIP this vector region!     │
│                                 │
│ Result: No duplicate captures   │
└─────────────────────────────────┘
         ↓

FINAL OUTPUT: 2 images (correct!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ page5_img1.png (Raster A)
✓ page5_img2.png (Raster B)
```

## Edge Cases Handled

### Case 1: Pure Vector Diagram (No Rasters)
```
┌────────────────────┐
│  ╭─────╮           │  No raster images
│  │ SVG │←──→       │  on this page
│  ╰─────╯           │
│    ↓               │  Overlap check:
│  [Box]             │  - No rasters to compare
│                    │
│  Pure vector!      │  Result: KEEP vector ✓
└────────────────────┘
```

### Case 2: Separate Vector + Raster (No Overlap)
```
┌────────────────────────────┐
│ ┌──────┐                   │  Vector diagram
│ │Vector│                   │  and raster in
│ └──────┘                   │  different areas
│                            │
│              ┌──────┐      │  Overlap check:
│              │Raster│      │  - No intersection
│              └──────┘      │
│                            │  Result: KEEP both ✓
└────────────────────────────┘
```

### Case 3: Vector Contains Raster (Your Issue!)
```
┌─────────────────────────────┐
│ Figure 4. Label             │  Large vector
│ ┌──────┐      ┌──────┐      │  encompasses
│ │Raster│      │Raster│      │  rasters + label
│ │  A   │      │  B   │      │
│ └──────┘      └──────┘      │  Overlap check:
│                             │  - A: 100% inside
└─────────────────────────────┘  - B: 100% inside
                               
Result: SKIP vector ✓ (your fix!)
```

## Threshold Tuning Guide

```
OVERLAP THRESHOLD VALUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

threshold = 0.1 (10%)
├─ AGGRESSIVE: Skip vectors with minimal raster overlap
├─ Pros: Fewest duplicates
└─ Cons: May skip legitimate vectors with small overlap

threshold = 0.2 (20%) ← RECOMMENDED DEFAULT
├─ BALANCED: Good compromise between dedup and accuracy
├─ Pros: Handles most Figure cases correctly
└─ Cons: Rare edge cases with intentional overlap

threshold = 0.5 (50%)
├─ CONSERVATIVE: Only skip vectors with major overlap
├─ Pros: Preserves most vectors
└─ Cons: May allow some duplicates through

threshold = 0.8 (80%)
├─ VERY CONSERVATIVE: Only skip near-complete overlap
├─ Pros: Safest for complex layouts
└─ Cons: May not catch all duplicates
```

## Configuration

To adjust the threshold, edit `Multipage_Image_Extractor.py` line 663:

```python
if raster_area > 0 and (intersection_area / raster_area) > 0.2:
                                                            ↑
                                                     Change this value
                                                     (0.0 to 1.0)
```

## Testing Your Changes

After adjusting settings, test with:

```bash
# Run automated tests
python3 test_raster_vector_overlap.py

# Process your PDF
python3 pdf_to_unified_xml.py your_file.pdf

# Check output in:
# - your_file_MultiMedia/ (should have no duplicates)
# - your_file_MultiMedia.xml (inspect <media> elements)
```

## Summary

✓ **Problem Solved:** Vector captures no longer duplicate raster images  
✓ **Smart Detection:** Size-independent overlap calculation  
✓ **Preserves Diagrams:** Pure vector drawings still captured  
✓ **Configurable:** Adjustable threshold for different use cases  
✓ **Well-Tested:** Test suite verifies correct behavior  
