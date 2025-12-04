#!/usr/bin/env python3
"""
Fix for ColId Weaving Issues on Single-Column Pages

This module contains improved ColId assignment logic that:
1. Detects single-column pages and assigns consistent ColId
2. Smooths out isolated ColId transitions
3. Reduces weaving between ColId 0 and 1

Can be integrated into pdf_to_excel_columns.py or used as a standalone fix.
"""

import statistics
from typing import List, Dict, Any


def is_single_column_page(fragments: List[Dict[str, Any]], col_starts: List[float], page_width: float) -> bool:
    """
    Detect if a page is truly single-column.
    
    A page is considered single-column if:
    1. Only one column start was detected, OR
    2. >80% of fragments are left-aligned to the same position (±20px), OR
    3. The page has very few column-2+ fragments
    
    Args:
        fragments: List of text fragments
        col_starts: Detected column start positions
        page_width: Width of the page
    
    Returns:
        True if page is single-column
    """
    if not fragments:
        return True
    
    # Criterion 1: Only one column detected
    if len(col_starts) <= 1:
        return True
    
    # Criterion 2: Check if >80% of fragments start at similar left position
    # This catches single-column pages with some indented content
    left_positions = [f["left"] for f in fragments]
    
    # Find the most common left position (mode)
    # Use a tolerance of 20 pixels to group similar positions
    left_groups = {}
    for left in left_positions:
        # Find if this left position matches an existing group
        matched = False
        for group_left in left_groups:
            if abs(left - group_left) < 20:
                left_groups[group_left] += 1
                matched = True
                break
        if not matched:
            left_groups[left] = 1
    
    if left_groups:
        max_group_count = max(left_groups.values())
        left_alignment_ratio = max_group_count / len(fragments)
        
        if left_alignment_ratio > 0.80:
            return True
    
    # Criterion 3: Check if page has actual multi-column content
    # If all fragments have ColId 0 or 1, and there's weaving, it's likely single-column
    if all(f.get("col_id") in (0, 1, None) for f in fragments):
        # Count transitions between 0 and 1
        col_ids = [f.get("col_id") for f in sorted(fragments, key=lambda x: x.get("baseline", 0))]
        col_ids = [c for c in col_ids if c is not None]
        
        if col_ids:
            transitions = sum(1 for i in range(1, len(col_ids)) 
                            if col_ids[i] != col_ids[i-1] and 
                            {col_ids[i], col_ids[i-1]} == {0, 1})
            
            # If there are many transitions (>5), likely a single-column page with weaving issue
            if transitions > 5:
                return True
    
    return False


def smooth_colid_transitions(fragments: List[Dict[str, Any]], min_group_size: int = 3) -> None:
    """
    Smooth out isolated ColId transitions to reduce weaving.
    
    If a small group (<min_group_size) of fragments has a different ColId
    than its neighbors, reassign to match neighbors.
    
    Example:
        Before: [0, 0, 0, 1, 1, 0, 0, 0]  (2 fragments with ColId 1)
        After:  [0, 0, 0, 0, 0, 0, 0, 0]  (smoothed to match neighbors)
    
    Args:
        fragments: List of text fragments (modified in-place)
        min_group_size: Minimum size for a group to be preserved
    """
    if not fragments:
        return
    
    # Sort by reading order (or baseline if reading order not set)
    fragments.sort(key=lambda f: (f.get("reading_order_index", 0), f.get("baseline", 0)))
    
    # Find isolated groups
    i = 0
    while i < len(fragments):
        current_col_id = fragments[i]["col_id"]
        group_start = i
        
        # Find end of current ColId group
        while i < len(fragments) and fragments[i]["col_id"] == current_col_id:
            i += 1
        
        group_size = i - group_start
        
        # If group is small and surrounded by different ColId, consider reassigning
        if group_size < min_group_size and group_start > 0 and i < len(fragments):
            prev_col_id = fragments[group_start - 1]["col_id"]
            next_col_id = fragments[i]["col_id"] if i < len(fragments) else None
            
            # Only reassign if isolated between same ColId
            if prev_col_id == next_col_id and prev_col_id != current_col_id:
                # Special case: Don't merge ColId 0 into ColId 1+ if the group spans full width
                # This prevents losing genuinely full-width content
                if current_col_id == 0:
                    # Check if any fragment in the group is truly full-width
                    page_width = max(f["left"] + f["width"] for f in fragments)
                    has_full_width = any(
                        f["width"] >= page_width * 0.60
                        for f in fragments[group_start:i]
                    )
                    if has_full_width:
                        continue  # Don't reassign full-width content
                
                # Reassign isolated group to match neighbors
                for j in range(group_start, i):
                    fragments[j]["col_id"] = prev_col_id


def assign_single_column_ids(fragments: List[Dict[str, Any]], use_col_id: int = 1) -> None:
    """
    Assign a consistent ColId to all fragments on a single-column page.
    
    Args:
        fragments: List of text fragments (modified in-place)
        use_col_id: ColId to assign (default: 1)
                   Use 1 to treat as "Column 1"
                   Use 0 to treat as "Full-width content"
    """
    for f in fragments:
        f["col_id"] = use_col_id


def improved_assign_column_ids(
    fragments: List[Dict[str, Any]],
    page_width: float,
    col_starts: List[float],
    enable_single_column_detection: bool = True,
    enable_smoothing: bool = True,
    single_column_colid: int = 1,
) -> None:
    """
    Improved column ID assignment with single-column detection and smoothing.
    
    This is a drop-in replacement for the original assign_column_ids() function
    with additional logic to reduce ColId weaving on single-column pages.
    
    Args:
        fragments: List of text fragments (modified in-place)
        page_width: Width of the page
        col_starts: Detected column start positions
        enable_single_column_detection: Enable single-column page detection
        enable_smoothing: Enable post-processing smoothing
        single_column_colid: ColId to use for single-column pages (1 or 0)
    """
    if not fragments:
        return
    
    # If there's effectively only one column start, treat everything as single column
    if len(col_starts) <= 1:
        assign_single_column_ids(fragments, use_col_id=single_column_colid)
        return
    
    # === Original assign_column_ids logic ===
    margin_ratio = 0.05
    left_margin = page_width * margin_ratio
    right_margin = page_width * (1.0 - margin_ratio)
    
    # Calculate column boundaries (midpoints between adjacent column starts)
    boundaries = []
    for i in range(len(col_starts) - 1):
        midpoint = (col_starts[i] + col_starts[i + 1]) / 2.0
        boundaries.append(midpoint)
    
    for f in fragments:
        left = f["left"]
        right = f["left"] + f["width"]
        width = f["width"]
        
        # Full-width if it essentially spans from near-left to near-right
        if left <= left_margin and right >= right_margin:
            f["col_id"] = 0
        elif width >= page_width * 0.45:
            f["col_id"] = 0
        else:
            # Assign based on LEFT edge position relative to boundaries
            if left < boundaries[0]:
                f["col_id"] = 1
            elif len(boundaries) > 1 and left >= boundaries[-1]:
                f["col_id"] = len(col_starts)
            else:
                # Find which column territory the left edge falls into
                for i in range(len(boundaries)):
                    if i == len(boundaries) - 1:
                        f["col_id"] = i + 2
                        break
                    elif left < boundaries[i + 1]:
                        f["col_id"] = i + 1
                        break
    
    # === NEW: Single-column detection ===
    if enable_single_column_detection:
        if is_single_column_page(fragments, col_starts, page_width):
            # Reassign all fragments to single column
            assign_single_column_ids(fragments, use_col_id=single_column_colid)
            return
    
    # === NEW: Smoothing ===
    if enable_smoothing:
        smooth_colid_transitions(fragments, min_group_size=3)


def analyze_colid_quality(fragments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the quality of ColId assignments on a page.
    
    Returns metrics about weaving, transitions, and other indicators
    of ColId assignment quality.
    
    Args:
        fragments: List of text fragments
    
    Returns:
        Dictionary with quality metrics:
        - transition_count: Number of ColId transitions
        - weaving_01_count: Number of transitions between ColId 0 and 1
        - unique_colids: Set of unique ColIds
        - has_weaving: Boolean indicating if weaving detected
        - colid_sequence: List of ColIds in reading order
    """
    if not fragments:
        return {
            "transition_count": 0,
            "weaving_01_count": 0,
            "unique_colids": set(),
            "has_weaving": False,
            "colid_sequence": [],
        }
    
    # Sort by reading order
    sorted_frags = sorted(fragments, key=lambda f: (
        f.get("reading_order_index", 0),
        f.get("baseline", 0)
    ))
    
    col_ids = [f["col_id"] for f in sorted_frags]
    unique_colids = set(col_ids)
    
    # Count all transitions
    transition_count = sum(1 for i in range(1, len(col_ids)) if col_ids[i] != col_ids[i-1])
    
    # Count weaving transitions (specifically between 0 and 1)
    weaving_01_count = sum(
        1 for i in range(1, len(col_ids))
        if col_ids[i] != col_ids[i-1] and {col_ids[i], col_ids[i-1]} == {0, 1}
    )
    
    # Weaving detected if >3 transitions between 0 and 1
    has_weaving = weaving_01_count > 3
    
    return {
        "transition_count": transition_count,
        "weaving_01_count": weaving_01_count,
        "unique_colids": unique_colids,
        "has_weaving": has_weaving,
        "colid_sequence": col_ids,
    }


# Example usage
if __name__ == "__main__":
    # Example: Apply fix to fragments
    example_fragments = [
        {"left": 72, "width": 100, "baseline": 100, "col_id": None, "reading_order_index": 1},
        {"left": 72, "width": 400, "baseline": 120, "col_id": None, "reading_order_index": 2},
        {"left": 108, "width": 350, "baseline": 140, "col_id": None, "reading_order_index": 3},
        {"left": 72, "width": 400, "baseline": 160, "col_id": None, "reading_order_index": 4},
    ]
    
    page_width = 612.0
    col_starts = [72.0]  # Single column detected
    
    print("Before fix:")
    print(f"Col starts: {col_starts}")
    
    # Apply original logic (simulated)
    for f in example_fragments:
        if f["width"] >= page_width * 0.45:
            f["col_id"] = 0
        else:
            f["col_id"] = 1
    
    print(f"ColId sequence: {[f['col_id'] for f in example_fragments]}")
    metrics = analyze_colid_quality(example_fragments)
    print(f"Weaving detected: {metrics['has_weaving']}")
    print(f"Transitions (0↔1): {metrics['weaving_01_count']}")
    
    # Reset for fix
    for f in example_fragments:
        f["col_id"] = None
    
    print("\nAfter fix:")
    improved_assign_column_ids(example_fragments, page_width, col_starts)
    print(f"ColId sequence: {[f['col_id'] for f in example_fragments]}")
    metrics = analyze_colid_quality(example_fragments)
    print(f"Weaving detected: {metrics['has_weaving']}")
    print(f"Transitions (0↔1): {metrics['weaving_01_count']}")
