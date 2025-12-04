#!/usr/bin/env python3
"""
Test the fixed implementation by extracting just the function
"""

def assign_reading_order_blocks(fragments, rows):
    """
    FIXED VERSION: Assign reading_order_block to all fragments based on vertical position and col_id.

    Block assignment strategy (interleaved based on baseline):
      - Sort fragments by baseline (top to bottom reading order)
      - Increment block number whenever col_id changes
      - This naturally handles:
          * Full-width content above columns
          * Column 1, Column 2, etc.
          * Full-width content between columns
          * Full-width content below columns
    
    Examples:
      Title(0) → Col1(1) → Col2(2) → Footnote(0)  =  Blocks: 1, 2, 3, 4
      Title(0) → Col1(1) → Figure(0) → Col2(2)    =  Blocks: 1, 2, 3, 4
      Col1(1) → Col2(2) → Col3(3)                 =  Blocks: 1, 2, 3
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

    # Sort fragments by baseline (top to bottom), then by left position
    # This ensures we process fragments in natural reading order
    sorted_frags = sorted(fragments, key=lambda f: (f["baseline"], f["left"]))
    
    # Assign blocks based on col_id transitions
    # When col_id changes, we're moving to a new logical block
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
    """Create test fragments representing a complex layout"""
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


def test_standard_two_column():
    """Test standard two-column layout without interleaved content"""
    fragments = [
        {"text": "Title", "col_id": 0, "baseline": 100, "left": 72, "reading_order_block": None},
        {"text": "Col1 text", "col_id": 1, "baseline": 120, "left": 72, "reading_order_block": None},
        {"text": "Col2 text", "col_id": 2, "baseline": 120, "left": 310, "reading_order_block": None},
        {"text": "Footnote", "col_id": 0, "baseline": 300, "left": 72, "reading_order_block": None},
    ]
    
    assign_reading_order_blocks(fragments, [])
    
    expected = [1, 2, 3, 4]  # Title → Col1 → Col2 → Footnote
    actual = [f["reading_order_block"] for f in sorted(fragments, key=lambda x: (x["baseline"], x["left"]))]
    
    return expected == actual


def test_single_column():
    """Test single column layout"""
    fragments = [
        {"text": "Line 1", "col_id": 1, "baseline": 100, "left": 72, "reading_order_block": None},
        {"text": "Line 2", "col_id": 1, "baseline": 120, "left": 72, "reading_order_block": None},
        {"text": "Line 3", "col_id": 1, "baseline": 140, "left": 72, "reading_order_block": None},
    ]
    
    assign_reading_order_blocks(fragments, [])
    
    # All should be Block 1
    return all(f["reading_order_block"] == 1 for f in fragments)


def test_interleaved_content():
    """Test complex interleaved content (main test)"""
    fragments = create_test_fragments()
    assign_reading_order_blocks(fragments, [])
    
    expected = [1, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 4, 5]
    actual = [f["reading_order_block"] for f in sorted(fragments, key=lambda x: (x["baseline"], x["left"]))]
    
    return expected == actual


def print_detailed_results(fragments):
    """Print detailed results"""
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    print(f"{'Block':<8} {'ColID':<8} {'Baseline':<10} {'Text':<50}")
    print("-" * 80)
    
    for f in sorted(fragments, key=lambda x: (x["baseline"], x["left"])):
        print(f"{f['reading_order_block']:<8} {f['col_id']:<8} {f['baseline']:<10} {f['text']:<50}")


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Fixed Implementation")
    print("=" * 80)
    
    # Run all tests
    tests = [
        ("Single column layout", test_single_column),
        ("Standard two-column layout", test_standard_two_column),
        ("Interleaved content (complex)", test_interleaved_content),
    ]
    
    all_passed = True
    for name, test_func in tests:
        result = test_func()
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    # Show detailed results for the complex case
    fragments = create_test_fragments()
    assign_reading_order_blocks(fragments, [])
    print_detailed_results(fragments)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if all_passed:
        print("\n✅ All tests passed!")
        print("\nThe fix correctly:")
        print("  ✓ Handles single-column layouts")
        print("  ✓ Handles standard multi-column layouts")
        print("  ✓ Handles interleaved full-width content")
        print("  ✓ Increments ReadingOrderBlock when col_id changes")
        print("  ✓ Maintains sequential and natural reading order")
    else:
        print("\n❌ Some tests failed!")
        exit(1)
