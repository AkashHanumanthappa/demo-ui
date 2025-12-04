# Content Sequencing Analysis

## Current Implementation

### How content is currently ordered in `_unified.xml`:

**Step 1: Excel Processing (`pdf_to_excel_columns.py`)**

1. **`assign_reading_order_blocks()`** (lines 140-210):
   - Assigns `reading_order_block` numbers based on content type:
     - Block 1: Full-width content ABOVE columns (col_id=0)
     - Block 2: First column (col_id=1)
     - Block 3: Second column (col_id=2)
     - Block N: Full-width content BELOW/WITHIN columns (col_id=0)

2. **`assign_reading_order_from_rows()`** (lines 57-137):
   - Assigns a **single sequential** `reading_order_index` (1, 2, 3, ...) across ALL fragments on the page
   - Uses "column-major" ordering:
     - Groups fragments into rows (by baseline)
     - Each row gets a "dominant column" (row_col)
     - Orders rows in column-major fashion:
       1. Full-width rows above columns (baseline ascending)
       2. Column 1 rows (baseline ascending)
       3. Column 2 rows (baseline ascending)
       4. Full-width rows below columns (baseline ascending)
     - Within each row, sorts fragments left-to-right

**Step 2: Unified XML Generation (`pdf_to_unified_xml.py`)**

Lines 877-881:
```python
sorted_fragments = sorted(
    page_data["fragments"],
    key=lambda x: (x["reading_order_block"], x["reading_order_index"])
)
```

- Sorts by: `(reading_order_block, reading_order_index)`
- This respects the pre-calculated `reading_order_index` which is already a global sequence

### Problem with Current Approach:

The `reading_order_index` is calculated ONCE across the entire page using a "dominant column per row" approach. This means:

1. **Row-based logic**: Fragments are grouped into rows first, then each row is assigned to a "dominant column"
2. **Row can have mixed ColIDs**: A single row might contain fragments with different `col_id` values
3. **No re-sorting by individual fragment attributes**: Once `reading_order_index` is assigned, it's used as-is

This works well for typical multi-column layouts, but doesn't match the desired behavior of:
- First sort by ReadingOrderBlock
- Then by individual fragment's ColID
- Then by individual fragment's Baseline

---

## Desired Implementation

### User's Requirements:

**3-Level Hierarchical Sorting:**

1. **Level 1**: ReadingOrderBlock numbers ascending (1, 2, 3, ...)
2. **Level 2**: Within each block, ColID from lowest to highest (0, 1, 2, 3, ...)
3. **Level 3**: Within each column, organize by Baseline ascending

### Key Differences:

| Aspect | Current | Desired |
|--------|---------|---------|
| **Primary Sort** | reading_order_block | ✓ Same: reading_order_block |
| **Secondary Sort** | reading_order_index (pre-calculated global sequence) | ❌ Different: col_id (individual fragment attribute) |
| **Tertiary Sort** | N/A (baked into reading_order_index) | ❌ Different: baseline (individual fragment attribute) |
| **Row Grouping** | Yes - fragments grouped by row, row assigned dominant column | No - each fragment sorted independently by its own col_id |
| **Baseline Grouping** | Yes - rows are sorted by baseline | Yes - but at fragment level, not row level |

### Example Scenario Where They Differ:

Imagine a page with 2 columns where fragments have the following properties:

```
Fragment A: reading_order_block=2, col_id=1, baseline=100
Fragment B: reading_order_block=2, col_id=2, baseline=95
Fragment C: reading_order_block=2, col_id=1, baseline=110
Fragment D: reading_order_block=2, col_id=2, baseline=105
```

**Current Implementation** (if reading_order_index was assigned in column-major order):
- Might produce: A (RO=1), C (RO=2), B (RO=3), D (RO=4)
- Order: A → C → B → D

**Desired Implementation** (sort by block → col_id → baseline):
- Sort: (2,1,100) → (2,1,110) → (2,2,95) → (2,2,105)
- Order: A → C → B → D

In this case they match, but consider if fragments were on different rows:

```
Fragment A: block=2, col_id=2, baseline=100, row_col=2
Fragment B: block=2, col_id=1, baseline=95, row_col=1
Fragment C: block=2, col_id=2, baseline=110, row_col=2
Fragment D: block=2, col_id=1, baseline=105, row_col=1
```

**Current Implementation** (column-major, processes column 1 fully first):
- Column 1 (baseline order): B (baseline=95), D (baseline=105)
- Column 2 (baseline order): A (baseline=100), C (baseline=110)
- Final order: B → D → A → C

**Desired Implementation** (sort by col_id then baseline):
- Col 1: B (95), D (105)
- Col 2: A (100), C (110)
- Final order: B → D → A → C

They match in this case too! But consider a more complex case:

```
Same reading block, but fragments have different col_ids even within same row
Fragment A: block=2, col_id=1, baseline=100, left=50
Fragment B: block=2, col_id=2, baseline=100, left=300
Fragment C: block=2, col_id=1, baseline=110, left=50
Fragment D: block=2, col_id=2, baseline=95, left=300
```

If the row-based logic groups A+B as a single row (same baseline), and assigns that row a "dominant column":

**Current Implementation**:
- Row 1 (baseline=100, dominant_col=1): A, B → reading_order_index: A=1, B=2
- Row 2 (baseline=110, dominant_col=1): C → reading_order_index: C=3
- Row 3 (baseline=95, dominant_col=2): D → reading_order_index: D=4
- Rows sorted column-major within block 2: Row1 → Row3 → Row2 (wait, this doesn't make sense)

Actually, looking at the code more carefully (lines 116-119 in pdf_to_excel_columns.py):
```python
for c in col_ids:
    col_rows = [r for r in row_infos if r["row_col"] == c]
    col_rows_sorted = sorted(col_rows, key=lambda r: r["baseline"])
    ordered_rows.extend(col_rows_sorted)
```

This processes each column fully (all rows in column 1, then all rows in column 2). So:
- Column 1 rows (by baseline): Row with baseline=100 (contains A,B but row_col=1), Row with baseline=110 (C)
- Column 2 rows (by baseline): Row with baseline=95 (D)
- Final: A, B, C, D

**Desired Implementation**:
- Sort by (block, col_id, baseline): (2,1,100), (2,1,110), (2,2,95), (2,2,100)
- Final: A, C, D, B

This is DIFFERENT! The key difference is that the current implementation groups fragments into rows first, then assigns each row to a dominant column. The desired implementation treats each fragment individually based on its own col_id.

---

## Recommendation

**Option 1: Change XML sorting (simplest)**

Modify the sorting in `pdf_to_unified_xml.py` line 877-881:

```python
# Current
sorted_fragments = sorted(
    page_data["fragments"],
    key=lambda x: (x["reading_order_block"], x["reading_order_index"])
)

# Change to
sorted_fragments = sorted(
    page_data["fragments"],
    key=lambda x: (x["reading_order_block"], x["col_id"], x["baseline"])
)
```

This will:
- ✓ Sort by reading_order_block first
- ✓ Then by col_id within each block
- ✓ Then by baseline within each column
- ✓ All information available in Excel (ReadingOrderBlock, ColID, Baseline)
- ✓ Matches user's requested logic exactly

**Option 2: Recalculate reading_order_index (more complex)**

Modify `assign_reading_order_from_rows()` to assign reading_order_index hierarchically:
1. Sort fragments by (reading_order_block, col_id, baseline)
2. Assign sequential reading_order_index in that order

This would make reading_order_index match the desired order, but requires more changes.

---

## Conclusion

The current implementation uses a **row-centric, column-major** approach where fragments are grouped into rows, rows are assigned to columns, and then rows are ordered column-by-column.

The desired implementation uses a **fragment-centric, hierarchical** approach where each fragment is sorted individually by (block, col_id, baseline).

**The simplest fix is Option 1**: Change the sorting key in `pdf_to_unified_xml.py` to use `(reading_order_block, col_id, baseline)` instead of `(reading_order_block, reading_order_index)`.
