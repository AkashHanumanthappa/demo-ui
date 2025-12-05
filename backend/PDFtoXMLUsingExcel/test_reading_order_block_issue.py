#!/usr/bin/env python3
"""
Test to demonstrate the ReadingOrderBlock numbering issue.

This test simulates a page with:
1. Full-width title at top (col_id=0, baseline=100)
2. Column 1 content (col_id=1, baseline=120-200)
3. Full-width figure in middle (col_id=0, baseline=220)
4. Column 2 content (col_id=2, baseline=240-320)
5. Full-width footnote at bottom (col_id=0, baseline=340)

Expected ReadingOrderBlock sequence: 1, 2, 3, 4, 5
Current (buggy) behavior: 1, 2, 3, 4, 4 (figure and footnote get same block)
"""

def assign_reading_order_blocks_CURRENT(fragments, rows):
    """
    Current implementation from pdf_to_excel_columns.py (lines 459-527)
    """
    if not fragments:
        return

    # Collect all unique col_ids
    all_col_ids = sorted({f["col_id"] for f in fragments if f["col_id"] is not None})

    # If everything is single column, assign Block 1 to all
    if len(all_col_ids) <= 1:
        for f in fragments:
            f["reading_order_block"] = 1
        return

    # Find non-zero columns and determine where they start vertically
    positive_cols = [c for c in all_col_ids if c > 0]

    if not positive_cols:
        # No multi-column content, everything is Block 1
        for f in fragments:
            f["reading_order_block"] = 1
        return

    # Find the minimum baseline of the first column to split full-width above/below
    first_col = min(positive_cols)
    col_fragments = [f for f in fragments if f["col_id"] == first_col]
    if col_fragments:
        first_col_min_baseline = min(f["baseline"] for f in col_fragments)
    else:
        first_col_min_baseline = float('inf')

    block_num = 1

    # Block 1: Full-width content ABOVE columns
    above_fullwidth = [
        f for f in fragments
        if f["col_id"] == 0 and f["baseline"] < first_col_min_baseline
    ]
    if above_fullwidth:
        for f in above_fullwidth:
            f["reading_order_block"] = block_num
        block_num += 1

    # Blocks 2+: Each column gets its own block number
    for col_id in positive_cols:
        col_frags = [f for f in fragments if f["col_id"] == col_id]
        if col_frags:
            for f in col_frags:
                f["reading_order_block"] = block_num
            block_num += 1

    # Final block: Full-width content BELOW/WITHIN columns
    below_fullwidth = [
        f for f in fragments
        if f["col_id"] == 0 and f["baseline"] >= first_col_min_baseline
    ]
    if below_fullwidth:
        for f in below_fullwidth:
            f["reading_order_block"] = block_num  # BUG: ALL get same block!


def assign_reading_order_blocks_FIXED(fragments, rows):
    """
    Fixed implementation - interleave blocks based on vertical position.
    """
    if not fragments:
        return

    # Collect all unique col_ids
    all_col_ids = sorted({f["col_id"] for f in fragments if f["col_id"] is not None})

    # If everything is single column, assign Block 1 to all
    if len(all_col_ids) <= 1:
        for f in fragments:
            f["reading_order_block"] = 1
        return

    # Sort fragments by baseline to process in reading order
    sorted_frags = sorted(fragments, key=lambda f: (f["baseline"], f["left"]))
    
    # Group consecutive fragments by col_id
    block_num = 0
    prev_col_id = None
    
    for frag in sorted_frags:
        current_col_id = frag["col_id"]
        
        # Start a new block when col_id changes
        if current_col_id != prev_col_id:
            block_num += 1
            prev_col_id = current_col_id
        
        frag["reading_order_block"] = block_num


def create_test_fragments():
    """
    Create test fragments representing a complex layout:
    - Full-width title at top
    - Column 1 content
    - Full-width figure in middle
    - Column 2 content  
    - Full-width footnote at bottom
    """
    fragments = [
        # Full-width title at top (should be Block 1)
        {"text": "CHAPTER TITLE", "col_id": 0, "baseline": 100, "left": 72},
        
        # Column 1 content (should be Block 2)
        {"text": "Column 1 line 1", "col_id": 1, "baseline": 120, "left": 72},
        {"text": "Column 1 line 2", "col_id": 1, "baseline": 140, "left": 72},
        {"text": "Column 1 line 3", "col_id": 1, "baseline": 160, "left": 72},
        {"text": "Column 1 line 4", "col_id": 1, "baseline": 180, "left": 72},
        {"text": "Column 1 line 5", "col_id": 1, "baseline": 200, "left": 72},
        
        # Full-width figure caption in middle (should be Block 3)
        {"text": "Figure 1: An illustration", "col_id": 0, "baseline": 220, "left": 72},
        
        # Column 2 content (should be Block 4)
        {"text": "Column 2 line 1", "col_id": 2, "baseline": 240, "left": 310},
        {"text": "Column 2 line 2", "col_id": 2, "baseline": 260, "left": 310},
        {"text": "Column 2 line 3", "col_id": 2, "baseline": 280, "left": 310},
        {"text": "Column 2 line 4", "col_id": 2, "baseline": 300, "left": 310},
        {"text": "Column 2 line 5", "col_id": 2, "baseline": 320, "left": 310},
        
        # Full-width footnote at bottom (should be Block 5)
        {"text": "1. This is a footnote", "col_id": 0, "baseline": 340, "left": 72},
    ]
    
    return fragments


def print_results(fragments, title):
    """Print fragments with their assigned reading order blocks."""
    print(f"\n{title}")
    print("=" * 80)
    print(f"{'Block':<8} {'ColID':<8} {'Baseline':<10} {'Text':<50}")
    print("-" * 80)
    
    for f in sorted(fragments, key=lambda x: (x["baseline"], x["left"])):
        print(f"{f['reading_order_block']:<8} {f['col_id']:<8} {f['baseline']:<10} {f['text']:<50}")


def verify_results(fragments, expected_blocks):
    """Verify that the reading order blocks match expected values."""
    issues = []
    
    for i, frag in enumerate(sorted(fragments, key=lambda x: (x["baseline"], x["left"]))):
        expected = expected_blocks[i]
        actual = frag["reading_order_block"]
        
        if expected != actual:
            issues.append(f"Fragment '{frag['text']}': expected block {expected}, got {actual}")
    
    return issues


if __name__ == "__main__":
    print("Testing ReadingOrderBlock Assignment")
    print("=" * 80)
    
    # Test 1: Current (buggy) implementation
    fragments_current = create_test_fragments()
    assign_reading_order_blocks_CURRENT(fragments_current, [])
    print_results(fragments_current, "CURRENT IMPLEMENTATION (BUGGY)")
    
    expected_blocks = [1, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 4, 5]
    issues_current = verify_results(fragments_current, expected_blocks)
    
    if issues_current:
        print("\n❌ ISSUES FOUND IN CURRENT IMPLEMENTATION:")
        for issue in issues_current:
            print(f"  - {issue}")
    else:
        print("\n✅ Current implementation: All blocks assigned correctly")
    
    # Test 2: Fixed implementation
    fragments_fixed = create_test_fragments()
    assign_reading_order_blocks_FIXED(fragments_fixed, [])
    print_results(fragments_fixed, "\nFIXED IMPLEMENTATION")
    
    issues_fixed = verify_results(fragments_fixed, expected_blocks)
    
    if issues_fixed:
        print("\n❌ ISSUES FOUND IN FIXED IMPLEMENTATION:")
        for issue in issues_fixed:
            print(f"  - {issue}")
    else:
        print("\n✅ Fixed implementation: All blocks assigned correctly")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nThe CURRENT implementation has a bug:")
    print("  - Full-width content in the middle (Figure caption, baseline=220)")
    print("    and at the bottom (Footnote, baseline=340) get the SAME block number")
    print("  - This is because ALL col_id=0 fragments below the first column")
    print("    are assigned to a single block")
    print("\nThe FIXED implementation correctly assigns sequential blocks based on")
    print("vertical position, resulting in proper reading order.")
