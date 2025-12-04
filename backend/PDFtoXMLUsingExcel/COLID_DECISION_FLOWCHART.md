# ColId Assignment Decision Flowchart

## High-Level Process Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PDF Page Processing                           │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│          Step 1: Detect Column Starts                            │
│                                                                   │
│  detect_column_starts(fragments, page_width)                    │
│  → Returns: col_starts = [72.0, 340.0, ...]                     │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│          Step 2: Assign Column IDs                               │
│                                                                   │
│  improved_assign_column_ids(fragments, page_width, col_starts) │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                ┌─────────────────────┴─────────────────────┐
                │                                             │
                ▼                                             ▼
    ┌────────────────────────┐                  ┌────────────────────────┐
    │  len(col_starts) <= 1? │                  │  Single-column page?   │
    │                        │                  │  (3 detection criteria)│
    └────────┬───────────────┘                  └────────┬───────────────┘
             │ YES                                        │ YES
             │                                            │
             ├────────────────────────────────────────────┤
             │                                            │
             ▼                                            ▼
    ┌─────────────────────────────────────────────────────────────┐
    │          Single-Column Detected                              │
    │                                                               │
    │  Assign all fragments: col_id = 1                           │
    │  → [1, 1, 1, 1, 1, 1, 1, ...]                               │
    └─────────────────────────────────────────────────────────────┘
                             │
                             │ NO (multi-column)
                             ▼
    ┌─────────────────────────────────────────────────────────────┐
    │          Multi-Column Page                                   │
    │                                                               │
    │  Apply width & position-based assignment                    │
    └─────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │          For Each Fragment:                                  │
    │                                                               │
    │  1. Full-width? (spans margins) → col_id = 0               │
    │  2. Wide? (width ≥ 45% page) → col_id = 0                  │
    │  3. Otherwise → col_id based on left edge position          │
    └─────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │          Step 3: Smoothing                                   │
    │                                                               │
    │  smooth_colid_transitions(fragments, min_group_size=3)      │
    │  → Remove isolated transitions                               │
    │  → [0,0,1,1,0,0] becomes [0,0,0,0,0,0]                     │
    └─────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │          Final ColId Assignments                             │
    │                                                               │
    │  All fragments have col_id assigned                         │
    │  Ready for ReadingOrderBlock assignment                     │
    └─────────────────────────────────────────────────────────────┘
```

---

## Single-Column Detection Logic

```
┌─────────────────────────────────────────────────────────────────┐
│     is_single_column_page(fragments, col_starts, page_width)   │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                ┌─────────────────────┴─────────────────────┐
                │                                             │
                ▼                                             ▼
    ┌────────────────────────┐              ┌────────────────────────┐
    │  Criterion 1:          │              │  Criterion 2:          │
    │  len(col_starts) <= 1? │              │  >80% left-aligned?    │
    └────────┬───────────────┘              └────────┬───────────────┘
             │ YES                                    │ YES
             └──────────────┬─────────────────────────┘
                            │
                            │               ┌────────────────────────┐
                            │               │  Criterion 3:          │
                            │               │  >5 transitions 0↔1?   │
                            │               └────────┬───────────────┘
                            │                        │ YES
                            └────────────────┬───────┘
                                             │
                                             ▼
                                ┌─────────────────────────┐
                                │  Return: True            │
                                │  (Single-column)         │
                                └─────────────────────────┘
                                             │
                                             │ NO
                                             ▼
                                ┌─────────────────────────┐
                                │  Return: False           │
                                │  (Multi-column)          │
                                └─────────────────────────┘
```

---

## Detailed Width-Based Assignment (Multi-Column)

```
                          ┌────────────────────┐
                          │  For each fragment │
                          └──────────┬─────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │  Calculate:                               │
              │  - left = f["left"]                      │
              │  - right = f["left"] + f["width"]        │
              │  - width = f["width"]                    │
              └──────────────────┬───────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────────┐
              │  Check 1: Spans both margins?             │
              │  (left ≤ 5% AND right ≥ 95%)             │
              └──────────────────┬───────────────────────┘
                                 │ YES
                                 ├─────────► col_id = 0 (Full-width)
                                 │
                                 │ NO
                                 ▼
              ┌──────────────────────────────────────────┐
              │  Check 2: Very wide?                      │
              │  (width ≥ 45% of page_width)             │
              └──────────────────┬───────────────────────┘
                                 │ YES
                                 ├─────────► col_id = 0 (Full-width)
                                 │
                                 │ NO
                                 ▼
              ┌──────────────────────────────────────────┐
              │  Check 3: Left edge position              │
              │                                            │
              │  Calculate boundaries:                     │
              │  boundary[i] = midpoint between            │
              │                col_starts[i] and           │
              │                col_starts[i+1]             │
              └──────────────────┬───────────────────────┘
                                 │
                                 ▼
         ┌────────────────────────┴────────────────────────┐
         │                                                   │
         ▼                                                   ▼
┌──────────────────────┐                    ┌──────────────────────┐
│  left < boundary[0]? │                    │  left ≥ boundary[-1]?│
│  → col_id = 1        │                    │  → col_id = N        │
└──────────────────────┘                    └──────────────────────┘
         │                                                   │
         │                                                   │
         └───────────────────────┬───────────────────────────┘
                                 │
                                 │ Between boundaries
                                 ▼
              ┌──────────────────────────────────────────┐
              │  Find which boundary territory:           │
              │  boundary[i] ≤ left < boundary[i+1]      │
              │  → col_id = i+1                           │
              └──────────────────────────────────────────┘
```

---

## Smoothing Algorithm

```
                    ┌────────────────────────────────┐
                    │  Sort fragments by reading     │
                    │  order (baseline, position)    │
                    └──────────────┬─────────────────┘
                                   │
                                   ▼
                    ┌────────────────────────────────┐
                    │  Scan through fragments        │
                    │  looking for ColId groups      │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────┴─────────────────┐
                    │  Find group:                   │
                    │  - Same ColId                  │
                    │  - Consecutive in reading order│
                    └──────────────┬─────────────────┘
                                   │
                                   ▼
              ┌───────────────────────────────────────────┐
              │  Is group size < min_group_size (3)?      │
              └───────────────┬───────────────────────────┘
                              │ YES
                              ▼
              ┌───────────────────────────────────────────┐
              │  Check neighbors:                          │
              │  - Previous ColId                          │
              │  - Next ColId                              │
              └───────────────┬───────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────────────┐
              │  Are neighbors same ColId?                 │
              │  AND different from group ColId?           │
              └───────────────┬───────────────────────────┘
                              │ YES
                              ▼
              ┌───────────────────────────────────────────┐
              │  Special check:                            │
              │  If group is ColId 0 AND has full-width   │
              │  content (width ≥ 60% page)?              │
              └───────────────┬───────────────────────────┘
                              │ NO
                              ▼
              ┌───────────────────────────────────────────┐
              │  Reassign group to neighbor ColId         │
              │  (smooth the transition)                   │
              └───────────────────────────────────────────┘
                              │
                              │ YES (has full-width)
                              ├──────────► Keep original ColId 0
                              │
                              ▼
              ┌───────────────────────────────────────────┐
              │  Continue to next group                    │
              └───────────────────────────────────────────┘

Example:
Before: [0, 0, 0, 1, 1, 0, 0, 0]  (group of 2 isolated ColId 1)
After:  [0, 0, 0, 0, 0, 0, 0, 0]  (smoothed to match neighbors)
```

---

## Decision Tree: Single Fragment Assignment

```
                          ┌──────────────┐
                          │  Fragment    │
                          │  (left, width)│
                          └───────┬──────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │  Is page single-column?   │
                    └─────────────┬─────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │ YES                                    │ NO
              ▼                                        ▼
    ┌─────────────────────┐            ┌──────────────────────────┐
    │  Assign col_id = 1  │            │  Is fragment full-width? │
    │  (single-column)    │            │  (spans margins OR       │
    │                     │            │   width ≥ 45% page)     │
    └─────────────────────┘            └──────────┬───────────────┘
              │                                    │
              │                        ┌───────────┴───────────┐
              │                        │ YES                    │ NO
              │                        ▼                        ▼
              │              ┌──────────────────┐   ┌──────────────────┐
              │              │  col_id = 0      │   │  Use left edge   │
              │              │  (full-width)    │   │  to determine    │
              │              │                  │   │  column 1,2,3... │
              │              └──────────────────┘   └──────────────────┘
              │                        │                        │
              └────────────────────────┴────────────────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────┐
                          │  Smoothing (if enabled) │
                          └──────────┬──────────────┘
                                     │
                                     ▼
                          ┌─────────────────────────┐
                          │  Final col_id assigned  │
                          └─────────────────────────┘
```

---

## Reading Order Impact

### BEFORE Fix (with weaving)

```
ColId Sequence:     [1, 0, 1, 0, 1, 0, 1, 0]
                     │  │  │  │  │  │  │  │
ReadingOrderBlock:  [1, 2, 3, 4, 5, 6, 7, 8]  ← 8 blocks!
                     └──┴──┴──┴──┴──┴──┴──┘
                     Fragmented continuous content

Problem:
┌──────────────────────────────────────────────────────┐
│  Block 1: "Chapter 1" (ColId 1)                      │
│  ─────────────────────────── Boundary Break          │
│  Block 2: "This chapter..." (ColId 0)                │
│  ─────────────────────────── Boundary Break          │
│  Block 3: "The main..." (ColId 1)                    │
│  ─────────────────────────── Boundary Break          │
│  Block 4: "Results..." (ColId 0)                     │
│  ─────────────────────────── Boundary Break          │
│  ...                                                  │
└──────────────────────────────────────────────────────┘
```

### AFTER Fix (no weaving)

```
ColId Sequence:     [1, 1, 1, 1, 1, 1, 1, 1]
                     └──┴──┴──┴──┴──┴──┴──┘
ReadingOrderBlock:  [1, 1, 1, 1, 1, 1, 1, 1]  ← 1 block!
                     Continuous unified content

Solution:
┌──────────────────────────────────────────────────────┐
│  Block 1: All content (ColId 1)                      │
│    - "Chapter 1"                                      │
│    - "This chapter discusses..."                     │
│    - "The main approach was..."                      │
│    - "Results indicate..."                           │
│    - "5.1 Methods"                                   │
│    - "The methodology used..."                       │
│    - ...                                             │
└──────────────────────────────────────────────────────┘
```

---

## Configuration Decision Tree

```
                    ┌────────────────────────────────┐
                    │  Choose configuration          │
                    └──────────────┬─────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │  What type of document?                 │
              └────────────────────┬────────────────────┘
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       │                           │                           │
       ▼                           ▼                           ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│  Single-col  │          │  Multi-col   │          │  Mixed       │
│  book        │          │  journal     │          │  document    │
└──────┬───────┘          └──────┬───────┘          └──────┬───────┘
       │                         │                         │
       ▼                         ▼                         ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│  Enable:     │          │  Enable:     │          │  Enable:     │
│  - Detection │          │  - Detection │          │  - Detection │
│  - Smoothing │          │  - Smoothing │          │  - Smoothing │
│  ColId: 1    │          │  ColId: 1    │          │  ColId: 1    │
└──────────────┘          └──────────────┘          └──────────────┘
       │                         │                         │
       ▼                         ▼                         ▼
    OPTIMAL                   OPTIMAL                   OPTIMAL
```

**Recommended Settings** (works for 95% of cases):
```python
improved_assign_column_ids(
    fragments, 
    page_width, 
    col_starts,
    enable_single_column_detection=True,   # Always enable
    enable_smoothing=True,                 # Always enable
    single_column_colid=1                  # Default: 1
)
```

---

## Summary Flowchart

```
┌─────────────────────────────────────────────────────────────┐
│                    PDF Processing                            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Detect Column Starts        │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Is Single-Column?           │
              └───────┬──────────────────────┘
                      │
          ┌───────────┴───────────┐
          │ YES                   │ NO
          ▼                       ▼
    ┌──────────┐          ┌──────────────┐
    │  Unified │          │  Width-based │
    │  ColId   │          │  Assignment  │
    └─────┬────┘          └──────┬───────┘
          │                      │
          │                      ▼
          │              ┌──────────────┐
          │              │  Smoothing   │
          │              └──────┬───────┘
          │                      │
          └──────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Final ColId         │
          │  Assignments         │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  ReadingOrderBlock   │
          │  Assignment          │
          └──────────────────────┘

RESULT: No weaving, correct reading order!
```

---

## Quick Reference: Decision Points

| Question | Check | Result |
|----------|-------|--------|
| Is page single-column? | `len(col_starts) <= 1` | → All ColId 1 |
| Are 80%+ fragments aligned? | `left_alignment_ratio > 0.80` | → Single-column |
| Excessive weaving? | `transitions > 5` | → Single-column |
| Fragment spans margins? | `left ≤ 5% AND right ≥ 95%` | → ColId 0 |
| Fragment very wide? | `width ≥ 45% page` | → ColId 0 |
| Small isolated group? | `group_size < 3` | → Smooth to neighbor |
| Has full-width content? | `width ≥ 60% page` | → Keep ColId 0 |

---

This flowchart provides a visual representation of the complete ColId assignment logic, from detection through final assignment and smoothing.
