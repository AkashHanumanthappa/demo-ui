# RittDocBook DTD Compliance Check for Lists

## DTD Findings

### Allowed List Elements (from dbpoolx.mod)

✅ **itemizedlist** - Bulleted lists
```dtd
<!ELEMENT itemizedlist (blockinfo?, title?, listpreamble*, listitem+)>
<!ATTLIST itemizedlist
    spacing (normal|compact) #IMPLIED
    mark CDATA #IMPLIED
    ...common attributes...
>
```

✅ **orderedlist** - Numbered lists
```dtd
<!ELEMENT orderedlist (blockinfo?, title?, listpreamble*, listitem+)>
<!ATTLIST orderedlist
    numeration (arabic|upperalpha|loweralpha|upperroman|lowerroman) #IMPLIED
    inheritnum (inherit|ignore) #IMPLIED
    continuation (continues|restarts) #IMPLIED
    spacing (normal|compact) #IMPLIED
    ...common attributes...
>
```

✅ **listitem** - List items (for both types)
```dtd
<!ELEMENT listitem (component.mix+)>
<!ATTLIST listitem
    override CDATA #IMPLIED
    ...common attributes...
>
```
**Important:** `listitem` MUST contain at least one element from `component.mix`, which includes `para`, `formalpara`, `simpara`, etc.

❌ **simplelist** - DISABLED
```dtd
<!ENTITY % simplelist.module "IGNORE">
```
This is explicitly disabled in `rittexclusions.mod` line 121.

---

## Current Code Issues

### Issue 1: Direct text in listitem ❌
**Current code (line 3120-3121):**
```python
listitem = etree.SubElement(current_list, "listitem")
para = etree.SubElement(listitem, "para")
para.text = text
```
✅ This is **CORRECT** - we're wrapping text in `<para>` which is required.

### Issue 2: Using simplelist ❌
**Status:** Not used in current code ✅

### Issue 3: List attributes
**Current code:** Missing optional attributes that could improve rendering:
- `spacing` attribute for compact lists
- `numeration` attribute for orderedlist types
- `mark` attribute for itemizedlist bullet styles

---

## Compliance Status

✅ **COMPLIANT**: Current XML generation follows DTD requirements
- Uses only `itemizedlist` and `orderedlist`
- Wraps text in `<para>` within `<listitem>`
- Does not use disabled `simplelist`

⚠️ **Could be enhanced**:
- Add `spacing` attribute for visual hints
- Add `numeration` for ordered list styles
- Add proper list nesting support
