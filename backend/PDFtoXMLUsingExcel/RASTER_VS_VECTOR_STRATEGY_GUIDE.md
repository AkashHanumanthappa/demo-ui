# Raster vs Vector: Which to Keep When They Overlap?

## The Question

When a vector drawing region contains raster images, we have two options:

1. **Keep Rasters, Skip Vector** (Current approach)
2. **Keep Vector, Delete Rasters** (Alternative approach)

Which is better? **It depends on your use case.**

---

## Comparison Matrix

| Aspect | Keep Rasters, Skip Vector | Keep Vector, Delete Rasters |
|--------|---------------------------|----------------------------|
| **Image Quality** | ✅ Original high-res images | ⚠️ Resampled at render DPI |
| **Semantic Correctness** | ✅ Preserves PDF structure | ❌ Flattens to pixels |
| **Text Searchability** | ✅ Captions as text | ❌ Captions as pixels |
| **Content Separation** | ✅ Individual images | ❌ Baked together |
| **Complete Diagrams** | ⚠️ May miss vector elements | ✅ Captures everything |
| **File Size** | ✅ Smaller (original images) | ❌ Larger (full render) |
| **Reusability** | ✅ Each image separate | ❌ Must crop from composite |
| **Best For** | Academic papers, textbooks | Flowcharts, annotated diagrams |

---

## Detailed Analysis

### Keep Rasters, Skip Vector (Current Approach)

#### ✅ Advantages

**1. Preserves Original Quality**
```
PDF contains:
- image1.png (1200×1200, 72 KB) ← Original embedded file

Raster extraction:
✓ Extracts exact original: 1200×1200, 72 KB

Vector rendering:
✗ Renders at 200 DPI: ~950×950, 180 KB (resampled + bloated)
```

**2. Maintains Semantic Structure**
```xml
<!-- Keeps semantic meaning -->
<media type="raster" file="diagram_a.png" />
<media type="raster" file="diagram_b.png" />
<text>Figure 4. Radiofrequency (RF) energy...</text>

<!-- vs flattened -->
<media type="vector" file="figure4_all.png" />
<!-- Caption burned into image, not searchable -->
```

**3. Enables Granular Reuse**
```
Scenario: You need to reference "Diagram A" in another document

With separate rasters:
✓ Copy diagram_a.png
✓ Add caption: "See Figure 4A"

With composite vector:
✗ Open figure4_all.png
✗ Crop out just Diagram A
✗ Lose quality from crop/resize
```

**4. Better for Downstream Processing**
```python
# Image analysis tools work better with individual images
for image in extracted_images:
    # OCR, object detection, classification
    analyze_image(image)  # Each image analyzed separately ✓

# vs composite
composite = load_vector_image()
# Must first segment/split the composite ✗
# Then analyze each part
```

#### ❌ Disadvantages

**1. May Lose Context**
```
PDF has:
┌─────────────────────────┐
│ ╭──→ 🔧 ──→ 📊 ─────╮   │  Flowchart with arrows
│ │                   │   │  connecting raster icons
│ ╰───────────────────╯   │
└─────────────────────────┘

Raster extraction:
✓ icon1.png (🔧)
✓ icon2.png (📊)
✗ Arrows connecting them lost!

Vector extraction would capture:
✓ Complete flowchart with all elements
```

**2. Incomplete Composite Figures**
```
Complex figure with:
- Vector borders/frames
- Raster subfigures A, B, C
- Vector labels and arrows

Raster extraction:
✓ subfigure_a.png
✓ subfigure_b.png  
✓ subfigure_c.png
✗ Layout/relationships lost
```

---

### Keep Vector, Delete Rasters (Alternative Approach)

#### ✅ Advantages

**1. Preserves Complete Diagrams**
```
Flowchart with icons:
┌─────────────────────────────────┐
│  Start → [🔧 Process] → End     │
│           ↓                     │
│       [📊 Report]               │
└─────────────────────────────────┘

Vector capture:
✓ Complete flowchart with all elements
✓ Arrows and connections preserved
✓ Layout intact
```

**2. Maintains Visual Context**
```
Annotated diagram:
┌─────────────────────────┐
│ Background photo        │  Photo with
│ ╭───→ "Key feature" ←───╮  vector annotations
│ │                      │
│ ╰──────────────────────╯
└─────────────────────────┘

Vector capture:
✓ Photo + annotations together
✓ Shows relationships
```

**3. Simpler for Complex Layouts**
```
Multi-panel figure:
┌─────────────────────────┐
│ A │ B │ C │  ← Labels   │  Panel figure
│ ───┼───┼───             │  with grid
│ D │ E │ F │             │  and labels
└─────────────────────────┘

Vector capture:
✓ One image with complete layout
✓ All labels and structure preserved
```

#### ❌ Disadvantages

**1. Quality Loss**
```
Original embedded image: 2400×2400 px
Vector render at 200 DPI: 1000×1000 px
Quality: 17% of original! ✗
```

**2. Content Flattening**
```
Before (structured):
- image1.png (can be indexed, searched, classified)
- image2.png (can be processed independently)
- caption (searchable text)

After (flattened):
- composite.png (all baked together)
- Everything is pixels, nothing searchable
```

**3. Storage Bloat**
```
Separate rasters:
- image1.png: 45 KB (optimized PNG)
- image2.png: 52 KB (optimized PNG)
Total: 97 KB

Composite vector render:
- composite.png: 340 KB (full page area, DPI overhead)
Total: 340 KB (3.5× larger!)
```

---

## Recommendation by Use Case

### Use "Keep Rasters, Skip Vector" (Current) For:

✅ **Academic Papers**
- High-quality images needed
- Figures referenced individually
- Text searchability important

✅ **Technical Documentation**
- Diagrams reused across documents
- Each figure stands alone
- Quality preservation critical

✅ **Textbooks**
- Individual image licensing/attribution
- Print quality requirements
- Separate figure numbering

### Use "Keep Vector, Delete Rasters" (Alternative) For:

✅ **Flowcharts & Process Diagrams**
- Rasters are just small icons
- Arrows/connections are critical
- Composite view needed

✅ **Annotated Screenshots**
- Photo + overlays inseparable
- Context requires both layers
- Annotations reference specific image areas

✅ **Complex Composite Figures**
- Multi-panel layouts with borders
- Grid arrangements with labels
- Relationship between panels is key

---

## Implementation Options

### Option 1: Current Approach (Default)

Already implemented! No changes needed.

```bash
python3 pdf_to_unified_xml.py your_file.pdf
# Keeps rasters, skips overlapping vectors
```

### Option 2: Alternative Approach (Keep Vectors)

Modify `Multipage_Image_Extractor.py` to:
1. Detect raster-vector overlap
2. Remove raster entries from XML when vector keeps them
3. Mark vector as "composite" containing rasters

**Implementation:**

```python
# In extract_media_and_tables() function
# After both raster and vector extraction:

def remove_redundant_rasters(page_el, raster_rects, vector_rects):
    """
    Alternative strategy: Remove rasters that are contained in vectors.
    Use this when you want complete composite diagrams.
    """
    # Get all media elements
    media_elements = page_el.findall("media")
    
    rasters_to_remove = []
    
    for media in media_elements:
        if media.get("type") != "raster":
            continue
        
        # Get raster bounds
        r_x1 = float(media.get("x1"))
        r_y1 = float(media.get("y1"))
        r_x2 = float(media.get("x2"))
        r_y2 = float(media.get("y2"))
        r_rect = fitz.Rect(r_x1, r_y1, r_x2, r_y2)
        
        # Check if any vector contains this raster
        for v_rect in vector_rects:
            # If >20% of raster inside vector, remove raster
            x_overlap = max(0, min(v_rect.x1, r_rect.x1) - max(v_rect.x0, r_rect.x0))
            y_overlap = max(0, min(v_rect.y1, r_rect.y1) - max(v_rect.y0, r_rect.y0))
            intersection = x_overlap * y_overlap
            raster_area = r_rect.width * r_rect.height
            
            if raster_area > 0 and (intersection / raster_area) > 0.2:
                rasters_to_remove.append(media)
                # Also delete the image file
                img_file = media.get("file")
                img_path = os.path.join(media_dir, img_file)
                if os.path.exists(img_path):
                    os.remove(img_path)
                break
    
    # Remove from XML
    for media in rasters_to_remove:
        page_el.remove(media)
```

### Option 3: Hybrid Approach (Smart Detection)

Best of both worlds - choose strategy based on content analysis:

```python
def should_keep_vector_over_rasters(vector_rect, raster_rects, drawings):
    """
    Decide whether to keep vector (and delete rasters) or vice versa.
    
    Keep vector if:
    - Contains many vector elements (arrows, connectors)
    - Rasters are small icons (< 100×100)
    - Has complex vector shapes connecting rasters
    
    Keep rasters if:
    - Rasters are large/high-quality
    - Vector is just a border/box
    - Minimal vector content besides rasters
    """
    # Count vector elements
    vector_element_count = count_vector_elements_in_region(vector_rect, drawings)
    
    # Check raster sizes
    large_rasters = sum(1 for r in raster_rects if r.width > 200 and r.height > 200)
    small_rasters = len(raster_rects) - large_rasters
    
    # Decision logic
    if vector_element_count > 10 and small_rasters > 0:
        return True  # Complex diagram with small icons - keep vector
    
    if large_rasters > 0 and vector_element_count < 5:
        return False  # Large images with simple border - keep rasters
    
    # Default: keep rasters (safer for quality)
    return False
```

---

## Your Figure 4 Example

Let's analyze your specific case:

```
Figure 4. Radiofrequency (RF) energy...
[Diagram A: 3D coordinate system]  [Diagram B: Rotating frame]
```

### Analysis

| Aspect | Details |
|--------|---------|
| **Raster sizes** | Both ~400×300 px (substantial) |
| **Vector content** | Label text + border rectangle |
| **Relationship** | Diagrams are independent (A and B) |
| **Use case** | Academic/scientific paper |
| **Reuse likelihood** | High (may reference each diagram separately) |

**Recommendation:** **Keep rasters, skip vector** (current approach) ✓

**Why:**
- Both diagrams are large/detailed → preserve quality
- Diagrams are independent → useful to have separate
- Label text should be searchable → keep as text, not pixels
- Vector doesn't add value → just a border box

---

## Conclusion

**Current approach (keep rasters) is correct for your use case!**

But now you understand:
- **When** the alternative makes sense (flowcharts, annotated diagrams)
- **Why** the current approach is better for academic figures
- **How** to implement the alternative if needed

### Quick Decision Guide

```
Does the vector region have substantial vector content
(arrows, annotations, connectors)?
    ├─ YES → Consider keeping vector
    │         (flowchart, annotated diagram)
    │
    └─ NO → Keep rasters (current approach)
              (figure with border, side-by-side images)

Are the raster images high-quality and independent?
    ├─ YES → Keep rasters ✓
    └─ NO (small icons) → Keep vector may be better
```

**For Figure 4 style cases: Current approach is optimal!**
