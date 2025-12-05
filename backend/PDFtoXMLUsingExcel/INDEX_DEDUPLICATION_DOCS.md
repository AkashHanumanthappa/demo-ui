# Raster-Vector Deduplication: Complete Documentation Index

## Overview

This documentation covers the solution to duplicate image captures when processing PDFs with figures that contain multiple raster images alongside labels.

---

## Quick Links

### 🎯 Start Here

**[ANSWER_TO_YOUR_QUESTION.md](ANSWER_TO_YOUR_QUESTION.md)**  
Complete answer to "Why not delete rasters and keep vector?" with detailed analysis for your Figure 4 scenario.

**[WHICH_STRATEGY_TO_USE.md](WHICH_STRATEGY_TO_USE.md)**  
Decision guide: When to keep rasters vs vectors, with examples and recommendations.

### 📖 Main Documentation

**[README_DEDUPLICATION_FIX.md](README_DEDUPLICATION_FIX.md)**  
Complete guide with usage instructions, testing, configuration, and troubleshooting.

**[SOLUTION_SUMMARY.md](SOLUTION_SUMMARY.md)**  
High-level overview of the problem, solution, and how to use it.

### 🔧 Technical Details

**[RASTER_VECTOR_DEDUPLICATION_FIX.md](RASTER_VECTOR_DEDUPLICATION_FIX.md)**  
Technical deep-dive: root cause analysis, implementation details, and configuration.

**[DEDUPLICATION_VISUAL_GUIDE.md](DEDUPLICATION_VISUAL_GUIDE.md)**  
Visual diagrams explaining the problem and solution with ASCII art examples.

**[RASTER_VS_VECTOR_STRATEGY_GUIDE.md](RASTER_VS_VECTOR_STRATEGY_GUIDE.md)**  
Comprehensive comparison of both strategies with use case analysis.

### 🧪 Testing & Tools

**[test_raster_vector_overlap.py](test_raster_vector_overlap.py)**  
Automated test suite for verifying overlap detection logic.

**[alternative_strategy_example.py](alternative_strategy_example.py)**  
Script to implement the alternative approach (keep vectors, delete rasters) if needed.

---

## Problem Summary

When processing PDFs with figures containing multiple side-by-side images:

**Before Fix:**
```
Figure 4 with 2 diagrams → 3 files extracted:
├─ diagram_a.png (raster) ✓
├─ diagram_b.png (raster) ✓
└─ figure4_vector.png (duplicate of both) ✗
```

**After Fix:**
```
Figure 4 with 2 diagrams → 2 files extracted:
├─ diagram_a.png (raster) ✓
└─ diagram_b.png (raster) ✓
(Vector correctly skipped)
```

---

## Solution Overview

Modified `Multipage_Image_Extractor.py` to use **raster containment ratio** instead of IoU:

```python
# If > 20% of any raster is inside vector region, skip the vector
overlap_ratio = intersection_area / raster_area
if overlap_ratio > 0.2:
    skip_vector = True
```

**Result:** Automatic deduplication, no configuration needed!

---

## Document Guide

### For Quick Understanding

1. Read **[ANSWER_TO_YOUR_QUESTION.md](ANSWER_TO_YOUR_QUESTION.md)** first
   - Directly answers your question about deleting rasters
   - Shows why current approach is better for your use case
   - Includes quality/usage comparisons

### For Implementation

2. Read **[README_DEDUPLICATION_FIX.md](README_DEDUPLICATION_FIX.md)**
   - How to use the fix (it's automatic!)
   - Testing instructions
   - Configuration options
   - Troubleshooting guide

### For Strategy Decisions

3. Read **[WHICH_STRATEGY_TO_USE.md](WHICH_STRATEGY_TO_USE.md)**
   - When to keep rasters (your Figure 4 case)
   - When to keep vectors (flowcharts, etc.)
   - Decision tree and examples

### For Technical Details

4. Read **[RASTER_VECTOR_DEDUPLICATION_FIX.md](RASTER_VECTOR_DEDUPLICATION_FIX.md)**
   - Root cause analysis
   - Algorithm explanation
   - Performance impact
   - Edge cases

### For Visual Learners

5. Read **[DEDUPLICATION_VISUAL_GUIDE.md](DEDUPLICATION_VISUAL_GUIDE.md)**
   - ASCII diagrams showing the problem
   - Visual explanation of IoU vs containment
   - Processing flow diagrams
   - Threshold tuning guide

### For Alternative Approaches

6. Read **[RASTER_VS_VECTOR_STRATEGY_GUIDE.md](RASTER_VS_VECTOR_STRATEGY_GUIDE.md)**
   - Comprehensive comparison matrix
   - Detailed analysis of both strategies
   - Use case recommendations
   - Implementation options

---

## Code Files

### Main Fix

**`Multipage_Image_Extractor.py`** (lines 646-671)
- Improved overlap detection logic
- Automatically skips vectors containing rasters
- No configuration needed (works out-of-the-box)

### Testing

**`test_raster_vector_overlap.py`**
```bash
# Run tests to verify the fix
python3 test_raster_vector_overlap.py
```

Tests:
- ✓ Figure with multiple images + label (skip vector)
- ✓ Pure vector diagram (keep vector)
- ✓ Edge cases with minor overlap

### Alternative Strategy

**`alternative_strategy_example.py`**
```bash
# If you need to keep vectors and delete rasters
python3 alternative_strategy_example.py your_file.pdf
```

Use only for:
- Flowcharts with small embedded icons
- Annotated screenshots
- Complex composite figures where vector is essential

---

## Usage Examples

### Your Figure 4 (Default - Recommended)

```bash
# Just process normally - fix is automatic!
python3 pdf_to_unified_xml.py your_file.pdf --full-pipeline

# Output:
# ✓ page5_img1.png (Diagram A)
# ✓ page5_img2.png (Diagram B)
# (No duplicate vector)
```

### Flowchart with Icons (Alternative Strategy)

```bash
# Step 1: Process normally
python3 pdf_to_unified_xml.py flowchart.pdf

# Step 2: Keep vectors, remove rasters
python3 alternative_strategy_example.py flowchart.pdf

# Output:
# ✓ page1_vector1.png (complete flowchart)
# (Small icon rasters removed)
```

---

## Key Concepts

### Overlap Detection Methods

**IoU (Old method - Failed):**
```
IoU = intersection / (area1 + area2 - intersection)
Problem: Size-dependent, fails for large vector + small raster
```

**Containment Ratio (New method - Works!):**
```
Overlap = intersection / raster_area
Solution: Size-independent, correctly detects raster containment
```

### Strategy Comparison

| Aspect | Keep Rasters (Default) | Keep Vectors (Alternative) |
|--------|----------------------|---------------------------|
| Quality | ✅ Original high-res | ⚠️ Rendered at DPI |
| Granularity | ✅ Individual images | ❌ Baked together |
| Searchability | ✅ Text preserved | ❌ Text as pixels |
| Best for | Academic figures | Flowcharts |

---

## Configuration

### Default Settings (Recommended)

- Overlap threshold: **20%** (0.2)
- Automatic: **Yes**
- Debug logging: **Disabled**

### Adjust Threshold

Edit `Multipage_Image_Extractor.py` line 663:

```python
if raster_area > 0 and (intersection_area / raster_area) > 0.2:
                                                            ↑
                                                    Change: 0.1-0.5
```

### Enable Debug Logging

Uncomment line 670 in `Multipage_Image_Extractor.py`:

```python
if skip_vector:
    print(f"    Page {page_no}: Skipping vector region - {skip_reason}")
    continue
```

---

## Testing

### Quick Test

```bash
python3 test_raster_vector_overlap.py
```

Expected output:
```
✓ TEST PASSED: Figure with two side-by-side images + label
✓ TEST PASSED: Pure vector diagram (no raster overlap)
✓ ALL TESTS PASSED
```

### Test Your PDF

```bash
# Process your PDF
python3 pdf_to_unified_xml.py your_file.pdf

# Check results
ls -lh your_file_MultiMedia/
cat your_file_MultiMedia.xml | grep '<media'
```

---

## FAQ

### Q: Why not delete rasters and keep vector?

**A:** For your Figure 4, keeping rasters is better because:
- ✅ Higher quality (original images)
- ✅ Separate diagrams (can reference A or B individually)
- ✅ Searchable caption (accessibility)

See **[ANSWER_TO_YOUR_QUESTION.md](ANSWER_TO_YOUR_QUESTION.md)** for full answer.

### Q: When should I use the alternative strategy?

**A:** Only for:
- Flowcharts with small embedded icons
- Annotated screenshots
- Diagrams where vector elements (arrows, etc.) are essential

See **[WHICH_STRATEGY_TO_USE.md](WHICH_STRATEGY_TO_USE.md)** for decision guide.

### Q: How do I know if it's working?

**A:** Run the test suite or enable debug logging:
```bash
python3 test_raster_vector_overlap.py  # Automated tests
```

### Q: Can I adjust the threshold?

**A:** Yes! Edit line 663 in `Multipage_Image_Extractor.py`:
- Lower (0.1) = More aggressive deduplication
- Higher (0.5) = More conservative

See **[README_DEDUPLICATION_FIX.md](README_DEDUPLICATION_FIX.md)** for details.

---

## Summary

✅ **Problem Fixed:** Duplicate captures eliminated  
✅ **Automatic:** No configuration needed  
✅ **Tested:** Comprehensive test suite  
✅ **Documented:** Complete guides available  
✅ **Flexible:** Alternative strategy available if needed  

**For your Figure 4: Current approach is optimal! No changes needed.** 🎯

---

## Document Changelog

| Document | Purpose | Best For |
|----------|---------|----------|
| INDEX (this file) | Navigation | Finding right document |
| ANSWER_TO_YOUR_QUESTION | Direct answer | Understanding why rasters > vectors |
| WHICH_STRATEGY_TO_USE | Decision guide | Choosing the right approach |
| README_DEDUPLICATION_FIX | Usage guide | Using the fix |
| SOLUTION_SUMMARY | Quick overview | Executive summary |
| RASTER_VECTOR_DEDUPLICATION_FIX | Technical details | Understanding implementation |
| DEDUPLICATION_VISUAL_GUIDE | Visual explanation | Visual learners |
| RASTER_VS_VECTOR_STRATEGY_GUIDE | Strategy comparison | Comprehensive analysis |

---

## Next Steps

1. ✅ **You're done!** The fix is already applied and working.

2. 📖 **Read [ANSWER_TO_YOUR_QUESTION.md](ANSWER_TO_YOUR_QUESTION.md)** to understand why the current approach is better for your use case.

3. 🧪 **Optionally test:** Run `python3 test_raster_vector_overlap.py`

4. 🎯 **Continue using** `pdf_to_unified_xml.py` as normal - deduplication is automatic!

**No further action needed - your Figure 4 scenario is handled correctly!** ✓
