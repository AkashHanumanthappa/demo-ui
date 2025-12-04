# List Detection Analysis

## Summary
Your list detection is indeed **very aggressive** and may be catching text that isn't actually part of lists. Here's what's happening:

---

## Location of List Detection

### 1. Pattern Definitions (Line 876)
```python
ORDERED_LIST_RE = re.compile(r"^(?:\(?\d+[\.\)]|[A-Za-z][\.)])\s+")
```

### 2. Detection Function (Lines 1516-1527)
```python
def _is_list_item(text: str, mapping: dict) -> tuple[bool, str, str]:
    stripped = text.lstrip()
    pdf_cfg = mapping.get("pdf", {})
    markers = pdf_cfg.get("list_markers", [])
    
    # Check custom bullet markers FIRST
    for marker in markers:
        if stripped.startswith(marker):
            remainder = stripped[len(marker) :].strip()
            return True, "itemized", remainder or text.strip()
    
    # Then check ordered list patterns
    if ORDERED_LIST_RE.match(stripped):
        remainder = ORDERED_LIST_RE.sub("", stripped, count=1).strip()
        return True, "ordered", remainder or stripped
    
    return False, "", text
```

### 3. Usage in Main Processing Loop (Lines 2722-2742)
When processing text blocks, **every line** is checked for list markers before being considered as a paragraph.

### 4. Default Markers Configuration (Line 3301)
```python
mapping = {
    "pdf": {
        "list_markers": ["•", "◦", "▪", "–", "-"],
    },
    "font_roles": font_roles
}
```

---

## What Gets Matched (Examples)

### Bullet List Markers (Itemized Lists)
✅ Intended matches:
- `"• First item"`
- `"◦ Nested item"`
- `"▪ Another bullet"`
- `"– Em dash bullet"`
- `"- Simple dash"`

⚠️ **Problematic matches**:
- `"- Dr. Smith's research"` → Treated as a list item
- `"- 50 degrees"` → Treated as a list item (em dash in ranges)
- Any line starting with a hyphen, even if it's not a list

### Ordered List Pattern (Numbers/Letters)
The regex `^(?:\(?\d+[\.\)]|[A-Za-z][\.)])\s+` matches:

✅ Intended matches:
- `"1. First item"`
- `"2) Second item"`
- `"(3. Third item"`
- `"A. Option A"`
- `"b) Option B"`

⚠️ **VERY Problematic matches**:
- `"A. Smith conducted research"` → Treated as list item!
- `"I. Introduction"` → Could be a section header, treated as list
- `"a. k. a. (also known as)"` → First part matches
- `"3. 5 million dollars"` → Number at start
- `"e. g. for example"` → Single letter followed by period

---

## Why It's Too Aggressive

### 1. **Single Letter Pattern**
The pattern `[A-Za-z][\.)]` matches **any single letter** followed by a period or closing paren:
- Catches abbreviations like "A. Smith", "e. g.", "i. e."
- Catches sentence fragments
- No minimum context required

### 2. **No Context Checking**
The detection doesn't consider:
- Font size (might be a heading)
- Indentation level
- Previous/next line context
- Whether there are multiple consecutive list items

### 3. **Hyphen/Dash Ambiguity**
The marker `"-"` is extremely common:
- Used in ranges: "10-20 items"
- Used in compound words at line start
- Used as em-dash for emphasis

### 4. **No Word Length Check**
Even if the "remainder" text after the marker is very long or complex, it's still considered a list item.

---

## Where Detection Happens in Pipeline

```
PDF → XML → Parse Lines → Label Blocks → DocBook XML
                              ↑
                         LIST DETECTION
                         (checks EVERY line)
```

In `label_blocks()` function (~line 1901), the processing order is:
1. ✅ Book titles
2. ✅ Chapter headings  
3. ✅ Section headings
4. ✅ Captions
5. ⚠️ **List items** ← Too early, catches too much
6. ✅ Paragraphs (fallback)

---

## Recommendations to Fix

### Option 1: Tighten the Regex Pattern
**Current:**
```python
ORDERED_LIST_RE = re.compile(r"^(?:\(?\d+[\.\)]|[A-Za-z][\.)])\s+")
```

**Suggested:**
```python
# Require at least 2 characters after marker, and avoid common abbreviations
ORDERED_LIST_RE = re.compile(r"^(?:\(?\d+[\.\)]|[A-HJ-Za-hj-z][\.)])\s+(?=\w{2,})")
```
Changes:
- Excludes `I.` and `i.` (often Roman numerals for sections)
- Requires at least 2 word characters after the marker (lookahead `(?=\w{2,})`)

### Option 2: Add Context Checking
Only treat as list item if:
- Multiple consecutive lines have the same pattern
- Indentation is consistent
- Text after marker is reasonable length (< 100 chars for first line)

### Option 3: Make Markers More Specific
```python
"list_markers": ["• ", "◦ ", "▪ ", "– "]  # Include trailing space
```
And remove plain hyphen `"-"` from default markers.

### Option 4: Add List Detection Threshold
Require at least 2-3 consecutive lines matching list patterns before committing to list structure.

### Option 5: Order of Detection
Move list detection **after** paragraph grouping, then check if paragraph looks like a list item.

---

## Quick Test Command

To see what's being detected as lists in your output:
```bash
# Search for list_item blocks in your processing
grep -A 3 '"label": "list_item"' output.json

# Or if outputting XML:
grep -A 2 '<listitem>' output.xml | head -30
```

Would you like me to implement any of these fixes?
