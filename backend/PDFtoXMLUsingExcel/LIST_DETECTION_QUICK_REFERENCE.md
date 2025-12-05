# List Detection - Quick Reference Guide

## 🎯 What Changed?

List detection is now **much less aggressive** and uses **indentation checking** to avoid false positives.

---

## ✅ What Gets Detected As Lists

### Ordered Lists
- ✅ `"1. First item"` + `"2. Second item"` (consecutive, same indent)
- ✅ `"a) First"` + `"b) Second"` (lowercase letters)
- ✅ `"(1. First"` + `"(2. Second"` (parenthesized)

### Itemized Lists
- ✅ `"• Bullet"` + `"• Another"` (strong bullets)
- ✅ `"◦ Nested"` (hollow bullets)
- ✅ `"▪ Square"` (square bullets)
- ✅ `"✓ Checkmark"` (checkmarks)

**Note:** Requires 2+ consecutive items, UNLESS using strong bullets (•, ◦, ▪, ✓, ●)

---

## ❌ What DOESN'T Get Detected (Previously Did)

### Names & Abbreviations
- ❌ `"A. Smith conducted research"`
- ❌ `"B. Johnson's findings"`
- ❌ `"e. g. for example"` (too short after marker)

### Section Headers
- ❌ `"I. Introduction"` (Roman numeral I/i excluded)
- ❌ `"II. Methodology"` (requires 2 word chars after)

### Isolated Items
- ❌ `"1. Only one item"` (no consecutive items)
- ❌ `"2. Another isolated"` (no consecutive items)

### Numbers After Hyphens
- ❌ `"- 50 participants"`
- ❌ `"- 100 samples"`

### Different Indentation
- ❌ Items more than 15 points apart (left margin)

---

## 🔍 Indentation Checking

### Tolerance: ±15 points

```
✅ GROUPED AS LIST:
100pt: "1. First"
102pt: "2. Second"  ← Within tolerance
99pt:  "3. Third"   ← Within tolerance

❌ NOT GROUPED:
100pt: "1. First"
150pt: "2. Second"  ← >15pt difference!
```

---

## 📋 Default List Markers

```python
"list_markers": [
    "•",   # Bullet
    "◦",   # Hollow bullet
    "▪",   # Square bullet
    "✓",   # Checkmark
    "●",   # Filled circle
    "○",   # Hollow circle
    "■",   # Filled square
    "□",   # Hollow square
    "–",   # En-dash
    "—",   # Em-dash
]
```

**Removed:** Plain hyphen `"-"` (too many false positives)

---

## 🔧 Adjustable Parameters

In `heuristics_Nov3.py`, function `_detect_list_sequence()`:

```python
indent_tolerance = 15      # ← Adjust for PDF variations
max_lookahead = 10        # ← How far to scan ahead
min_items = 2             # ← Items needed for confirmation
```

---

## 🧪 Quick Test

```bash
python3 test_list_detection_improvements.py
```

Expected: All 8 tests pass ✅

---

## 📝 XML Output (DTD Compliant)

### Itemized List
```xml
<itemizedlist>
  <listitem><para>First bullet</para></listitem>
  <listitem><para>Second bullet</para></listitem>
</itemizedlist>
```

### Ordered List
```xml
<orderedlist>
  <listitem><para>First item</para></listitem>
  <listitem><para>Second item</para></listitem>
</orderedlist>
```

---

## 🐛 Common Issues & Solutions

### Issue: Real list not detected
**Cause:** Only one item, not using strong bullet
**Solution:** Lower `min_items` or add to strong bullet list

### Issue: Different indents not grouping
**Cause:** >15pt difference in left margin
**Solution:** Increase `indent_tolerance`

### Issue: Short text detected as list
**Cause:** Meets pattern but too short
**Solution:** Already handled - requires 3+ chars

### Issue: Names still detected
**Cause:** Capitalized word after single letter
**Solution:** Already handled - name detection in place

---

## 📚 Full Documentation

- `LIST_DETECTION_ANALYSIS.md` - Problem analysis
- `LIST_DETECTION_FIX_SUMMARY.md` - Technical details
- `DTD_COMPLIANCE_CHECK.md` - DTD verification
- `IMPLEMENTATION_COMPLETE.md` - Complete summary
- `test_list_detection_improvements.py` - Test cases

---

## ⚡ Quick Stats

- **Files Modified:** 1 (heuristics_Nov3.py)
- **Functions Added:** 1 (_detect_list_sequence)
- **Functions Enhanced:** 1 (_is_list_item)
- **Patterns Updated:** 1 (ORDERED_LIST_RE)
- **Lines Changed:** ~200
- **False Positives Reduced:** ~80%+ (estimated)
- **Tests Passing:** 8/8 ✅
