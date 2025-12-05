#!/usr/bin/env python3
"""
Test the actual fixed implementation in pdf_to_excel_columns.py
"""

import sys
sys.path.insert(0, '/workspace')

from pdf_to_excel_columns import assign_reading_order_blocks

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
        {"text": "CHAPTER TITLE", "col_id": 0, "baseline": 100, "left": 72, "reading_order_block": None},
        
        # Column 1 content (should be Block 2)
        {"text": "Column 1 line 1", "col_id": 1, "baseline": 120, "left": 72, "reading_order_block": None},
        {"text": "Column 1 line 2", "col_id": 1, "baseline": 140, "left": 72, "reading_order_block": None},
        {"text": "Column 1 line 3", "col_id": 1, "baseline": 160, "left": 72, "reading_order_block": None},
        {"text": "Column 1 line 4", "col_id": 1, "baseline": 180, "left": 72, "reading_order_block": None},
        {"text": "Column 1 line 5", "col_id": 1, "baseline": 200, "left": 72, "reading_order_block": None},
        
        # Full-width figure caption in middle (should be Block 3)
        {"text": "Figure 1: An illustration", "col_id": 0, "baseline": 220, "left": 72, "reading_order_block": None},
        
        # Column 2 content (should be Block 4)
        {"text": "Column 2 line 1", "col_id": 2, "baseline": 240, "left": 310, "reading_order_block": None},
        {"text": "Column 2 line 2", "col_id": 2, "baseline": 260, "left": 310, "reading_order_block": None},
        {"text": "Column 2 line 3", "col_id": 2, "baseline": 280, "left": 310, "reading_order_block": None},
        {"text": "Column 2 line 4", "col_id": 2, "baseline": 300, "left": 310, "reading_order_block": None},
        {"text": "Column 2 line 5", "col_id": 2, "baseline": 320, "left": 310, "reading_order_block": None},
        
        # Full-width footnote at bottom (should be Block 5)
        {"text": "1. This is a footnote", "col_id": 0, "baseline": 340, "left": 72, "reading_order_block": None},
    ]
    
    return fragments


def print_results(fragments):
    """Print fragments with their assigned reading order blocks."""
    print("\nActual Implementation Results:")
    print("=" * 80)
    print(f"{'Block':<8} {'ColID':<8} {'Baseline':<10} {'Text':<50}")
    print("-" * 80)
    
    for f in sorted(fragments, key=lambda x: (x["baseline"], x["left"])):
        print(f"{f['reading_order_block']:<8} {f['col_id']:<8} {f['baseline']:<10} {f['text']:<50}")


def verify_results(fragments):
    """Verify that the reading order blocks match expected values."""
    expected = [1, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 4, 5]
    issues = []
    
    sorted_frags = sorted(fragments, key=lambda x: (x["baseline"], x["left"]))
    
    for i, frag in enumerate(sorted_frags):
        expected_block = expected[i]
        actual_block = frag["reading_order_block"]
        
        if expected_block != actual_block:
            issues.append(f"Fragment '{frag['text']}': expected block {expected_block}, got {actual_block}")
    
    return issues


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Real Implementation from pdf_to_excel_columns.py")
    print("=" * 80)
    
    # Test the actual implementation
    fragments = create_test_fragments()
    assign_reading_order_blocks(fragments, [])
    print_results(fragments)
    
    # Verify results
    issues = verify_results(fragments)
    
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n✅ SUCCESS: All blocks assigned correctly!")
        print("\nExpected sequence: 1 → 2 → 2 → 2 → 2 → 2 → 3 → 4 → 4 → 4 → 4 → 4 → 5")
        print("Actual sequence:   ", end="")
        sorted_frags = sorted(fragments, key=lambda x: (x["baseline"], x["left"]))
        print(" → ".join(str(f["reading_order_block"]) for f in sorted_frags))
        print("\n✓ ReadingOrderBlock increments correctly when col_id changes")
        print("✓ Full-width content between columns gets its own block")
        print("✓ Sequential and natural reading order maintained")
        sys.exit(0)
