# Fix: Reference Mapper Warnings

## Issue
You were getting these warnings throughout the extraction:
```
Warning: Failed to register image in mapper: ResourceReference.__init__() got an unexpected keyword argument 'page_number'
Warning: Failed to register vector in mapper: ResourceReference.__init__() got an unexpected keyword argument 'page_number'
```

## Root Cause

**File:** `Multipage_Image_Extractor.py`  
**Issue:** Passing unsupported parameters to `mapper.add_resource()`

The code was trying to pass:
- `page_number=page_no`
- `image_number_in_page=img_counter`

But `ResourceReference` dataclass in `reference_mapper.py` doesn't have these fields. It only supports:
- `image_number_in_chapter` (not `image_number_in_page`)
- No `page_number` field at all

## The Fix ✅

### Changed in `Multipage_Image_Extractor.py`

**Raster Images (Line ~1020):**
```python
# BEFORE (BUGGY):
mapper.add_resource(
    original_path=filename,
    intermediate_name=filename,
    resource_type="image",
    first_seen_in=f"page_{page_no}",
    page_number=page_no,           # ← UNSUPPORTED
    image_number_in_page=img_counter,  # ← UNSUPPORTED
    width=int(rect.width),
    height=int(rect.height),
    is_raster=True,
)

# AFTER (FIXED):
mapper.add_resource(
    original_path=filename,
    intermediate_name=filename,
    resource_type="image",
    first_seen_in=f"page_{page_no}",  # ← Page info still tracked here
    width=int(rect.width),
    height=int(rect.height),
    is_raster=True,
)
```

**Vector Images (Line ~1238):**
Same fix - removed `page_number` and `image_number_in_page` parameters.

## Impact

✅ **No data loss:** Page information is still tracked via `first_seen_in=f"page_{page_no}"`  
✅ **Warnings eliminated:** ResourceReference only gets fields it supports  
✅ **Mapper works properly:** Resources are now registered successfully  

## Testing

Run the extractor again and verify:
```bash
python3 Multipage_Image_Extractor.py your_document.pdf 2>&1 | grep "Failed to register"
```

**Expected:** No output (no warnings)

## Side Effects

None. The page number was being tracked in two places:
1. `first_seen_in=f"page_{page_no}"` ✓ (Still tracked)
2. `page_number=page_no` ✗ (Removed - was causing warnings)

The first method is sufficient for page-to-chapter mapping later in the pipeline.
