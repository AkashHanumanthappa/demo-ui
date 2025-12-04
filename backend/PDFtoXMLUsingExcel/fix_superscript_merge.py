#!/usr/bin/env python3
"""
Fix for Superscript/Subscript Merge Issue

Implements two-pass merging with script detection to handle cases like:
- Scientific notation: 10^7
- Chemical formulas: H2O
- Reference markers: [1]
- Ordinals: 1st, 2nd

Recommended: Option 4 (Two-pass merging with detection)
"""

import statistics
from typing import List, Dict, Any, Tuple


def detect_potential_script(fragment: Dict[str, Any], all_fragments: List[Dict[str, Any]], index: int) -> bool:
    """
    Detect if a fragment is likely a superscript or subscript.
    
    Criteria:
    - Small width (< 20px)
    - Small height (< 12px) 
    - Short text (≤ 3 characters)
    - Adjacent to larger fragment (within 5px horizontally)
    
    Args:
        fragment: Fragment to check
        all_fragments: All fragments on page (for adjacency check)
        index: Index of fragment in all_fragments
    
    Returns:
        True if likely a super/subscript
    """
    # Size criteria
    if fragment["width"] >= 20:
        return False
    if fragment["height"] >= 12:
        return False
    
    # Text length criteria
    text = fragment.get("text", "")
    if len(text) > 3:
        return False
    
    # Check adjacency to larger fragments
    prev_frag = all_fragments[index - 1] if index > 0 else None
    next_frag = all_fragments[index + 1] if index < len(all_fragments) - 1 else None
    
    has_adjacent_larger = False
    
    # Check previous fragment
    if prev_frag and prev_frag["height"] > fragment["height"]:
        # Calculate horizontal gap
        prev_right = prev_frag["left"] + prev_frag["width"]
        gap = fragment["left"] - prev_right
        if abs(gap) < 5:  # Within 5px
            has_adjacent_larger = True
    
    # Check next fragment
    if next_frag and next_frag["height"] > fragment["height"]:
        # Calculate horizontal gap
        frag_right = fragment["left"] + fragment["width"]
        gap = next_frag["left"] - frag_right
        if abs(gap) < 5:  # Within 5px
            has_adjacent_larger = True
    
    return has_adjacent_larger


def find_script_parent(
    script_fragment: Dict[str, Any],
    all_fragments: List[Dict[str, Any]],
    script_index: int,
    relaxed_baseline_tol: float = 8.0
) -> Tuple[int, str]:
    """
    Find the parent fragment for a super/subscript.
    
    Args:
        script_fragment: The super/subscript fragment
        all_fragments: All fragments on page
        script_index: Index of script fragment
        relaxed_baseline_tol: Relaxed baseline tolerance for scripts
    
    Returns:
        (parent_index, script_type) where script_type is "superscript" or "subscript"
        Returns (-1, "") if no parent found
    """
    script_baseline = script_fragment["baseline"]
    script_left = script_fragment["left"]
    script_right = script_left + script_fragment["width"]
    
    # Look for adjacent fragments within relaxed baseline tolerance
    for i, candidate in enumerate(all_fragments):
        if i == script_index:
            continue
        
        # Must be larger than script
        if candidate["height"] <= script_fragment["height"]:
            continue
        
        # Check baseline proximity (relaxed tolerance)
        baseline_diff = abs(candidate["baseline"] - script_baseline)
        if baseline_diff > relaxed_baseline_tol:
            continue
        
        # Check horizontal adjacency
        cand_left = candidate["left"]
        cand_right = cand_left + candidate["width"]
        
        # Is script to the right of candidate? (superscript/subscript after text)
        if abs(script_left - cand_right) < 5:
            # Determine if super or subscript based on vertical position
            if script_fragment["top"] < candidate["top"]:
                return (i, "superscript")
            else:
                return (i, "subscript")
        
        # Is script to the left of candidate? (rare, but possible)
        if abs(cand_left - script_right) < 5:
            if script_fragment["top"] < candidate["top"]:
                return (i, "superscript")
            else:
                return (i, "subscript")
    
    return (-1, "")


def merge_script_with_parent(
    parent: Dict[str, Any],
    script: Dict[str, Any],
    script_type: str
) -> Dict[str, Any]:
    """
    Merge a super/subscript with its parent fragment.
    
    Args:
        parent: Parent fragment
        script: Super/subscript fragment
        script_type: "superscript" or "subscript"
    
    Returns:
        Merged fragment
    """
    merged = dict(parent)  # Copy parent
    
    # Merge text with marker
    if script_type == "superscript":
        # Use caret notation: 10^7
        merged["text"] = parent["text"] + "^" + script["text"]
    else:
        # Use underscore notation: H_2
        merged["text"] = parent["text"] + "_" + script["text"]
    
    # Update normalized text
    merged["norm_text"] = " ".join(merged["text"].split()).lower()
    
    # Merge inner_xml if present
    if "inner_xml" in parent and "inner_xml" in script:
        merged["inner_xml"] = parent["inner_xml"] + script["inner_xml"]
    
    # Expand width to include script
    script_right = script["left"] + script["width"]
    parent_right = parent["left"] + parent["width"]
    new_right = max(script_right, parent_right)
    merged["width"] = new_right - parent["left"]
    
    # Keep parent's baseline (more reliable)
    merged["baseline"] = parent["baseline"]
    
    # Mark as merged
    merged["merged_script"] = True
    merged["script_count"] = parent.get("script_count", 0) + 1
    
    return merged


def group_fragments_with_script_detection(
    fragments: List[Dict[str, Any]],
    baseline_tol: float
) -> List[List[Dict[str, Any]]]:
    """
    Two-pass grouping with superscript/subscript detection.
    
    Pass 1: Detect potential scripts
    Pass 2: Merge scripts with parents using relaxed baseline tolerance
    Pass 3: Group remaining fragments into lines with normal tolerance
    
    Args:
        fragments: List of fragments sorted by baseline, left
        baseline_tol: Normal baseline tolerance
    
    Returns:
        List of rows (each row is a list of fragments)
    """
    if not fragments:
        return []
    
    # Sort by left position first (to detect adjacency properly)
    # Baseline sorting happens after merging
    fragments = sorted(fragments, key=lambda f: (f["top"], f["left"]))
    
    # Pass 1: Detect potential scripts
    for i, f in enumerate(fragments):
        f["is_potential_script"] = detect_potential_script(f, fragments, i)
    
    # Pass 2: Merge scripts with parents
    merged_fragments = []
    merged_indices = set()
    
    for i, f in enumerate(fragments):
        if i in merged_indices:
            continue
        
        if f.get("is_potential_script"):
            # Try to find parent
            parent_idx, script_type = find_script_parent(f, fragments, i)
            
            if parent_idx >= 0:
                # Merge with parent
                parent = fragments[parent_idx]
                
                # If parent already processed, update it in merged_fragments
                if parent_idx in merged_indices:
                    # Find parent in merged_fragments
                    for mf in merged_fragments:
                        if mf.get("original_index") == parent_idx:
                            # Merge script into this parent
                            merged = merge_script_with_parent(mf, f, script_type)
                            # Update in place
                            mf.update(merged)
                            merged_indices.add(i)
                            break
                else:
                    # Merge and add
                    merged = merge_script_with_parent(parent, f, script_type)
                    merged["original_index"] = parent_idx
                    merged_fragments.append(merged)
                    merged_indices.add(parent_idx)
                    merged_indices.add(i)
                
                continue
        
        # Not a script or no parent found
        if i not in merged_indices:
            f["original_index"] = i
            merged_fragments.append(f)
            merged_indices.add(i)
    
    # Pass 3: Group into lines using normal tolerance
    fragments = merged_fragments
    
    # Re-sort by baseline for grouping
    fragments = sorted(fragments, key=lambda f: (f["baseline"], f["left"]))
    
    lines = []
    current = []
    current_baseline = None
    
    for f in fragments:
        b = f["baseline"]
        if current_baseline is None:
            current = [f]
            current_baseline = b
        elif abs(b - current_baseline) <= baseline_tol:
            current.append(f)
        else:
            if current:
                lines.append(current)
            current = [f]
            current_baseline = b
    
    if current:
        lines.append(current)
    
    return lines


def improved_group_fragments_into_lines(
    fragments: List[Dict[str, Any]],
    baseline_tol: float,
    enable_script_detection: bool = True
) -> List[List[Dict[str, Any]]]:
    """
    Drop-in replacement for group_fragments_into_lines() with script detection.
    
    Args:
        fragments: List of fragments
        baseline_tol: Baseline tolerance
        enable_script_detection: Enable super/subscript detection
    
    Returns:
        List of rows
    """
    if not enable_script_detection:
        # Fall back to original logic
        lines = []
        current = []
        current_baseline = None
        
        for f in fragments:
            b = f["baseline"]
            if current_baseline is None:
                current = [f]
                current_baseline = b
            elif abs(b - current_baseline) <= baseline_tol:
                current.append(f)
            else:
                if current:
                    lines.append(current)
                current = [f]
                current_baseline = b
        
        if current:
            lines.append(current)
        
        return lines
    
    # Use improved logic with script detection
    return group_fragments_with_script_detection(fragments, baseline_tol)


# Example usage and testing
if __name__ == "__main__":
    # Test case: 10^7 (superscript)
    print("="*80)
    print("TEST: Superscript Merging")
    print("="*80)
    
    fragments = [
        {
            "top": 191,
            "left": 101,
            "width": 428,
            "height": 18,
            "baseline": 209,
            "text": "detail shortly, MRI uses radio waves with frequencies around 10",
            "norm_text": "detail shortly, mri uses radio waves with frequencies around 10",
        },
        {
            "top": 192,
            "left": 529,
            "width": 5,
            "height": 11,
            "baseline": 203,
            "text": "7",
            "norm_text": "7",
        }
    ]
    
    print("\nOriginal fragments:")
    for i, f in enumerate(fragments):
        print(f"  {i}: '{f['text']}' (baseline={f['baseline']}, left={f['left']}, width={f['width']})")
    
    baseline_tol = 2.0
    
    # Test original grouping
    print(f"\nOriginal grouping (baseline_tol={baseline_tol}):")
    rows_original = []
    current = []
    current_baseline = None
    for f in sorted(fragments, key=lambda x: (x["baseline"], x["left"])):
        b = f["baseline"]
        if current_baseline is None:
            current = [f]
            current_baseline = b
        elif abs(b - current_baseline) <= baseline_tol:
            current.append(f)
        else:
            rows_original.append(current)
            current = [f]
            current_baseline = b
    if current:
        rows_original.append(current)
    
    print(f"  Result: {len(rows_original)} rows")
    for i, row in enumerate(rows_original):
        print(f"    Row {i+1}: {len(row)} fragments - {[f['text'] for f in row]}")
    
    # Test improved grouping with debug
    print(f"\nImproved grouping with script detection:")
    print(f"  (Debug enabled)")
    
    # Make a copy and manually run detection with debug
    test_frags = [dict(f) for f in fragments]
    test_frags = sorted(test_frags, key=lambda f: (f["top"], f["left"]))
    
    print(f"\n  After sorting by top, left:")
    for i, f in enumerate(test_frags):
        print(f"    {i}: '{f['text']}' (top={f['top']}, left={f['left']}, baseline={f['baseline']}, h={f['height']}, w={f['width']})")
    
    print(f"\n  Detection phase:")
    for i, f in enumerate(test_frags):
        is_script = detect_potential_script(f, test_frags, i)
        f["is_potential_script"] = is_script
        print(f"    {i}: '{f['text']}' → is_script={is_script}")
    
    print(f"\n  Finding parents:")
    for i, f in enumerate(test_frags):
        if f.get("is_potential_script"):
            parent_idx, script_type = find_script_parent(f, test_frags, i)
            print(f"    {i}: '{f['text']}' → parent_idx={parent_idx}, type={script_type}")
    
    rows_improved = improved_group_fragments_into_lines(
        fragments.copy(),
        baseline_tol,
        enable_script_detection=True
    )
    
    print(f"\n  Final result: {len(rows_improved)} rows")
    for i, row in enumerate(rows_improved):
        print(f"    Row {i+1}: {len(row)} fragments - {[f['text'] for f in row]}")
    
    print("\n" + "="*80)
    print("RESULT")
    print("="*80)
    
    if len(rows_improved) == 1 and len(rows_improved[0]) == 1:
        merged_text = rows_improved[0][0]["text"]
        print(f"✓ SUCCESS: Fragments merged into: '{merged_text}'")
        print(f"  Expected: '...around 10^7' or similar")
    elif len(rows_improved) == 1:
        print(f"✓ PARTIAL: Fragments in same row but not merged")
        print(f"  This is expected - inline merging happens in next step")
    else:
        print(f"✗ FAIL: Fragments still in separate rows")
        print(f"  Check detection criteria")
