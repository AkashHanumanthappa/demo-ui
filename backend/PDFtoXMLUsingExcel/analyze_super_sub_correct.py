#!/usr/bin/env python3
"""
Correct analysis of superscript/subscript detection using TOP position
"""

print("="*80)
print("SUPERSCRIPT/SUBSCRIPT DETECTION - CORRECT APPROACH")
print("="*80)

# Example 1: Superscript (10^7)
print("\n" + "="*80)
print("EXAMPLE 1: SUPERSCRIPT (10^7)")
print("="*80)

frags_super = [
    {
        "top": 191,
        "left": 101,
        "width": 428,
        "height": 18,
        "text": "detail shortly, MRI uses radio waves with frequencies around 10",
        "font": "11"
    },
    {
        "top": 192,
        "left": 529,
        "width": 5,
        "height": 11,
        "text": "7",
        "font": "20"
    },
    {
        "top": 191,
        "left": 534,
        "width": 166,
        "height": 18,
        "text": "-Hz (cycles per second). ",
        "font": "11"
    }
]

print("\nFragments:")
for i, f in enumerate(frags_super):
    print(f"  {i}: top={f['top']}, left={f['left']}, width={f['width']}, height={f['height']}")
    print(f"      text='{f['text']}'")

print("\nAnalysis of fragment 1 (the '7'):")
f_script = frags_super[1]
f_prev = frags_super[0]
f_next = frags_super[2]

print(f"\n  Fragment 1 (script candidate):")
print(f"    top={f_script['top']}, height={f_script['height']}")
print(f"    Small? width={f_script['width']} < 20, height={f_script['height']} < 12 → YES")

print(f"\n  Previous fragment (potential parent):")
print(f"    top={f_prev['top']}, height={f_prev['height']}")
print(f"    Horizontal adjacency: prev_right={f_prev['left'] + f_prev['width']} vs script_left={f_script['left']}")
print(f"    Gap: {f_script['left'] - (f_prev['left'] + f_prev['width'])} pixels")
print(f"    Adjacent? Gap={f_script['left'] - (f_prev['left'] + f_prev['width'])} ≤ 5 → YES")

print(f"\n  Vertical relationship:")
print(f"    prev_top={f_prev['top']}, script_top={f_script['top']}")
print(f"    Top difference: {f_script['top'] - f_prev['top']} pixels")
print(f"    Script is {'LOWER' if f_script['top'] > f_prev['top'] else 'HIGHER'} on page (remember: higher top = lower on page)")

print(f"\n  Height comparison:")
print(f"    prev_height={f_prev['height']}, script_height={f_script['height']}")
print(f"    Ratio: {f_script['height'] / f_prev['height']:.2f}")
print(f"    Script is smaller? {f_script['height']} < {f_prev['height']} → YES")

print(f"\n  CORRECT DETECTION LOGIC:")
print(f"    1. Script is small (w<20, h<12) ✓")
print(f"    2. Adjacent to larger text (gap ≤ 5px) ✓")
print(f"    3. Top difference small: |{f_script['top'] - f_prev['top']}| = {abs(f_script['top'] - f_prev['top'])} ≤ 3px ✓")
print(f"    4. Height smaller: {f_script['height']} < {f_prev['height']} ✓")
print(f"\n  → SUPERSCRIPT (because top difference is minimal despite being 'lower')")

# Example 2: Subscript (B_0)
print("\n" + "="*80)
print("EXAMPLE 2: SUBSCRIPT (B₀)")
print("="*80)

frags_sub = [
    {
        "top": 324,
        "left": 142,
        "width": 129,
        "height": 17,
        "text": "tons aligned with the ",
        "font": "19"
    },
    {
        "top": 324,
        "left": 271,
        "width": 10,
        "height": 17,
        "text": "B",
        "font": "18"
    },
    {
        "top": 331,
        "left": 281,
        "width": 9,
        "height": 13,
        "text": "Ø",
        "font": "16"
    },
    {
        "top": 324,
        "left": 290,
        "width": 65,
        "height": 17,
        "text": " field is di-",
        "font": "19"
    }
]

print("\nFragments:")
for i, f in enumerate(frags_sub):
    print(f"  {i}: top={f['top']}, left={f['left']}, width={f['width']}, height={f['height']}")
    print(f"      text='{f['text']}'")

print("\nAnalysis of fragment 2 (the 'Ø'):")
f_script = frags_sub[2]
f_prev = frags_sub[1]  # The "B"
f_next = frags_sub[3]

print(f"\n  Fragment 2 (script candidate):")
print(f"    top={f_script['top']}, height={f_script['height']}")
print(f"    Small? width={f_script['width']} < 20, height={f_script['height']} < 12 → NO (13)")
print(f"    BUT height < 15, so still small")

print(f"\n  Previous fragment (potential parent 'B'):")
print(f"    top={f_prev['top']}, height={f_prev['height']}")
print(f"    Horizontal adjacency: prev_right={f_prev['left'] + f_prev['width']} vs script_left={f_script['left']}")
print(f"    Gap: {f_script['left'] - (f_prev['left'] + f_prev['width'])} pixels")
print(f"    Adjacent? Gap={f_script['left'] - (f_prev['left'] + f_prev['width'])} ≤ 5 → YES")

print(f"\n  Vertical relationship:")
print(f"    prev_top={f_prev['top']}, script_top={f_script['top']}")
print(f"    Top difference: {f_script['top'] - f_prev['top']} pixels")
print(f"    Script is {'LOWER' if f_script['top'] > f_prev['top'] else 'HIGHER'} on page")

print(f"\n  Height comparison:")
print(f"    prev_height={f_prev['height']}, script_height={f_script['height']}")
print(f"    Ratio: {f_script['height'] / f_prev['height']:.2f}")
print(f"    Script is smaller? {f_script['height']} < {f_prev['height']} → YES")

print(f"\n  CORRECT DETECTION LOGIC:")
print(f"    1. Script is small (w<20, h<15) ✓")
print(f"    2. Adjacent to larger text (gap ≤ 5px) ✓")
print(f"    3. Top difference: {f_script['top'] - f_prev['top']} = {f_script['top'] - f_prev['top']} pixels")
print(f"    4. Height smaller: {f_script['height']} < {f_prev['height']} ✓")
print(f"\n  → SUBSCRIPT (because top is significantly lower: +{f_script['top'] - f_prev['top']}px)")

# Define thresholds
print("\n" + "="*80)
print("DETECTION THRESHOLDS")
print("="*80)

print("""
CRITERIA FOR SUPER/SUBSCRIPT DETECTION:

1. SIZE:
   - width < 20 pixels
   - height < 15 pixels (increased from 12 to catch more cases)
   - text length ≤ 3 characters

2. ADJACENCY:
   - Horizontal gap to larger text ≤ 5 pixels
   - Must be adjacent to text with height > script height

3. VERTICAL OFFSET:
   - Superscript: -3 ≤ top_diff ≤ +3 (within ±3px of parent top)
   - Subscript: +3 ≤ top_diff ≤ +10 (3-10px below parent top)
   
   Where top_diff = script.top - parent.top
   
4. TYPE DETERMINATION:
   If all criteria met:
   - top_diff ≤ 3: SUPERSCRIPT (script is at or above parent baseline)
   - top_diff > 3: SUBSCRIPT (script is clearly below parent baseline)

KEY INSIGHT:
- Use TOP position, NOT baseline!
- baseline = top + height is misleading for scripts with different heights
- TOP position directly indicates vertical placement on page
""")

print("\n" + "="*80)
print("RECOMMENDED APPROACH")
print("="*80)

print("""
def detect_script_type(script_frag, parent_frag):
    # Size check
    if script_frag["width"] >= 20 or script_frag["height"] >= 15:
        return None
    
    # Height check (must be smaller than parent)
    if script_frag["height"] >= parent_frag["height"]:
        return None
    
    # Horizontal adjacency
    gap = script_frag["left"] - (parent_frag["left"] + parent_frag["width"])
    if abs(gap) > 5:
        return None
    
    # Vertical offset (using TOP position!)
    top_diff = script_frag["top"] - parent_frag["top"]
    
    # Superscript: within ±3px of parent top (but not >= 3px which is subscript)
    if -3 <= top_diff < 3:
        return "superscript"
    
    # Subscript: 3-10px below parent top  
    elif 3 <= top_diff <= 10:
        return "subscript"
    
    return None
""")
