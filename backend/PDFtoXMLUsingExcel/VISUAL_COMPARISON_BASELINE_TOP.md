# Visual Comparison: Baseline vs TOP Trade-offs

## The Critical Question

**Should we use TOP or BASELINE for grouping fragments?**

**Answer**: **BOTH** - but for different purposes!

---

## Case 1: Drop Cap (Large First Letter)

### Visual Layout

```
┌──────────────────────────────────────┐
│                                       │
│   ┏━━━┓his is a paragraph that       │
│   ┃ T ┃starts with a large drop      │
│   ┃   ┃cap spanning three lines.     │
│   ┗━━━┛The drop cap is decorative.   │
│                                       │
└──────────────────────────────────────┘
```

### XML Fragments

```xml
<text top="100" left="10" width="30" height="48" font="36">T</text>
<text top="100" left="45" width="200" height="12" font="12">his is a paragraph...</text>
<text top="115" left="10" width="210" height="12" font="12">cap spanning...</text>
<text top="130" left="10" width="210" height="12" font="12">The drop cap...</text>
```

### Analysis Using TOP

```
Fragment:  "T"      top=100
Fragment:  "his..." top=100
Difference: 0 pixels → SAME ROW

Result: "T" and "his..." would merge ❌ WRONG!
(Drop cap should span multiple lines)
```

### Analysis Using BASELINE

```
Fragment:  "T"      baseline=148 (100+48)
Fragment:  "his..." baseline=112 (100+12)
Fragment:  "cap..." baseline=127 (115+12)
Fragment:  "The..." baseline=142 (130+12)

Differences:
- "T" vs "his...": 36 pixels → DIFFERENT ROWS ✓
- "T" vs "cap...": 21 pixels → DIFFERENT ROWS ✓
- "T" vs "The...": 6 pixels → DIFFERENT ROWS ✓

Result: Drop cap correctly spans 3 lines ✓ CORRECT!
```

---

## Case 2: Superscript (10⁷)

### Visual Layout

```
┌──────────────────────────────────────┐
│                                       │
│   ...around 10⁷Hz (cycles per...)    │
│                ↑                      │
│                └─ Superscript         │
│                                       │
└──────────────────────────────────────┘
```

### XML Fragments

```xml
<text top="191" left="101" width="428" height="18">...around 10</text>
<text top="192" left="529" width="5" height="11">7</text>
<text top="191" left="534" width="166" height="18">Hz...</text>
```

### Analysis Using BASELINE

```
Fragment:  "...10"  baseline=209 (191+18)
Fragment:  "7"      baseline=203 (192+11)
Fragment:  "Hz..."  baseline=209 (191+18)

Differences:
- "...10" vs "7": 6 pixels → DIFFERENT ROWS ❌
- "7" vs "Hz...": 6 pixels → DIFFERENT ROWS ❌

Result: "10", "7", "Hz" are separate ❌ WRONG!
```

### Analysis Using TOP

```
Fragment:  "...10"  top=191
Fragment:  "7"      top=192
Fragment:  "Hz..."  top=191

Differences:
- "...10" vs "7": 1 pixel → SAME ROW ✓
- "7" vs "Hz...": 1 pixel → SAME ROW ✓

Result: Would merge into "...10⁷Hz" ✓ CORRECT!
```

---

## Case 3: Mixed Case (Apple and Orange)

### Visual Layout

```
┌──────────────────────────────────────┐
│                                       │
│   Apple and Orange                   │
│   ↑          ↑                        │
│   Capital    Lowercase                │
│   A          a                        │
│                                       │
└──────────────────────────────────────┘
```

### XML Fragments

```xml
<text top="100" left="10" width="50" height="18">Apple</text>
<text top="103" left="65" width="40" height="15">and</text>
<text top="100" left="110" width="60" height="18">Orange</text>
```

### Analysis Using TOP

```
Fragment:  "Apple"  top=100
Fragment:  "and"    top=103
Fragment:  "Orange" top=100

Differences:
- "Apple" vs "and": 3 pixels → Might split! ⚠
- "and" vs "Orange": 3 pixels → Might split! ⚠

Result: Risk of splitting mixed case text ❌
```

### Analysis Using BASELINE

```
Fragment:  "Apple"  baseline=118 (100+18)
Fragment:  "and"    baseline=118 (103+15)
Fragment:  "Orange" baseline=118 (100+18)

Differences:
- "Apple" vs "and": 0 pixels → SAME ROW ✓
- "and" vs "Orange": 0 pixels → SAME ROW ✓

Result: All merge correctly ✓ CORRECT!
```

---

## The Solution: Hybrid Approach

### Use BOTH, But Differently

```
┌─────────────────────────────────────────────────────┐
│                                                      │
│   Phase 1: DETECT SCRIPTS (using TOP)               │
│   ─────────────────────────────────────────────     │
│   • Look for SMALL fragments (w<15, h<12)           │
│   • Check TOP difference with adjacent larger text  │
│   • If top_diff ≤ 3: Mark as superscript           │
│   • If 3 < top_diff ≤ 10: Mark as subscript        │
│                                                      │
│   Phase 2: GROUP ROWS (using BASELINE)              │
│   ─────────────────────────────────────────────     │
│   • Group all fragments by baseline (unchanged)     │
│   • This preserves drop caps, mixed case, etc.      │
│                                                      │
│   Phase 3: CROSS-ROW MERGING                        │
│   ─────────────────────────────────────────────     │
│   • Merge marked scripts with their parents         │
│   • Even if they're in different rows               │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Example: Combined Approach

```
Input:
  Fragment 1: "T" (top=100, h=48) [Drop cap]
  Fragment 2: "his is 10" (top=100, h=12)
  Fragment 3: "7" (top=102, h=11) [Superscript]
  Fragment 4: "Hz" (top=100, h=12)

Phase 1 - Script Detection (using TOP):
  "T" → width=30, height=48 → NOT a script (too large) ✓
  "7" → width=5, height=11 → IS a script (small) ✓
       → top_diff vs "his is 10": 2 pixels → Superscript ✓

Phase 2 - Baseline Grouping:
  "T": baseline=148 }
  "his is 10": baseline=112 } Different rows
  "7": baseline=113        }  (by baseline)
  "Hz": baseline=112       }

Phase 3 - Cross-Row Merging:
  "7" marked as superscript of "his is 10"
  → Merge "7" into "his is 10" → "his is 10^7"
  → Then merge with "Hz" → "his is 10^7Hz" ✓

Result:
  Row 1: "T" (drop cap preserved) ✓
  Row 2: "his is 10^7Hz" (superscript merged) ✓
```

---

## Decision Matrix

| Case | Use TOP? | Use BASELINE? | Result |
|------|----------|---------------|--------|
| **Drop cap** | ❌ Would break | ✅ Works correctly | Use BASELINE |
| **Large first letter** | ❌ Would break | ✅ Works correctly | Use BASELINE |
| **Mixed case** | ❌ Might break | ✅ Works correctly | Use BASELINE |
| **Superscript** | ✅ Detects correctly | ❌ Misses it | Use TOP for detection |
| **Subscript** | ✅ Detects correctly | ❌ Misses it | Use TOP for detection |

**Conclusion**: Use BASELINE for grouping, TOP for script detection only!

---

## Strict Criteria for Script Detection

To avoid false positives, use VERY STRICT criteria:

```python
def is_potential_script(fragment, adjacent_larger):
    """
    VERY strict criteria to avoid misclassifying:
    - Drop caps
    - Large first letters
    - Bullets
    - Symbols
    """
    # Size: VERY small
    if fragment["width"] >= 15:  # Stricter than 20
        return False
    if fragment["height"] >= 12:  # Stricter than 15
        return False
    
    # Text: VERY short and alphanumeric
    text = fragment.get("text", "").strip()
    if len(text) > 3:
        return False
    if not text.isalnum():  # Only letters/numbers
        return False
    
    # Must be MUCH smaller than adjacent
    if fragment["height"] >= adjacent_larger["height"] * 0.75:
        return False  # Not small enough
    
    # Horizontal: VERY close
    gap = abs(fragment["left"] - (adjacent_larger["left"] + adjacent_larger["width"]))
    if gap > 5:
        return False
    
    # Vertical (using TOP): Within range
    top_diff = fragment["top"] - adjacent_larger["top"]
    if not (-3 <= top_diff <= 10):
        return False
    
    return True
```

---

## Test Matrix

| Input | Drop Cap? | Superscript? | Large Letter? | Mixed Case? |
|-------|-----------|--------------|---------------|-------------|
| width=30, height=48 | ✅ Detected | ❌ Not script | ✅ Detected | ❌ Not script |
| width=5, height=11 | ❌ Not drop | ✅ Script | ❌ Not large | ❌ Not script |
| width=20, height=24 | ❌ Not drop | ❌ Not script | ✅ Detected | ❌ Not script |
| width=50, height=18 | ❌ Not drop | ❌ Not script | ❌ Not large | ✅ Normal text |

---

## Summary

### The Problem
- **Baseline** works for normal text but misses superscripts/subscripts
- **TOP** detects superscripts/subscripts but breaks drop caps and mixed case

### The Solution
- **Phase 1**: Detect scripts using TOP (very strict criteria)
- **Phase 2**: Group rows using BASELINE (preserves existing behavior)
- **Phase 3**: Merge scripts across rows (surgical fix)

### The Benefit
- ✅ Superscripts merge: "10⁷" not "10" and "7"
- ✅ Subscripts merge: "B₀" not "B" and "Ø"
- ✅ Drop caps preserved: "T" spans multiple lines
- ✅ Large letters preserved: "Word" not split
- ✅ Mixed case preserved: "Apple and Orange" together
- ✅ No breaking changes to existing code

**This is the best of both worlds!**
