#!/usr/bin/env python3
"""
Simple test to verify the paragraph break logic with line width and position checks.
"""

import sys
sys.path.insert(0, '/home/user/PDFtoXMLUsingExcel')

from pdf_to_unified_xml import is_paragraph_break, calculate_column_boundaries

def test_paragraph_break_logic():
    """Test the paragraph break logic with different scenarios."""

    print("Testing paragraph break logic with line width/position checks...")
    print("=" * 70)

    # Create test fragments for a single column
    # Simulating a 612pt wide page (letter size), column from x=72 to x=540
    test_fragments = [
        {"left": 72, "width": 468, "top": 100, "height": 12, "col_id": 1, "text": "Full line extending to right", "reading_order_block": 1, "table_cell_id": ""},
        {"left": 72, "width": 468, "top": 112, "height": 12, "col_id": 1, "text": "Another full line here", "reading_order_block": 1, "table_cell_id": ""},
        {"left": 72, "width": 200, "top": 124, "height": 12, "col_id": 1, "text": "Short line", "reading_order_block": 1, "table_cell_id": ""},
        {"left": 72, "width": 468, "top": 136, "height": 12, "col_id": 1, "text": "Full line after short", "reading_order_block": 1, "table_cell_id": ""},
        {"left": 72, "width": 468, "top": 200, "height": 12, "col_id": 1, "text": "Full line with big gap", "reading_order_block": 1, "table_cell_id": ""},
    ]

    # Calculate column boundaries
    page_width = 612
    column_boundaries = calculate_column_boundaries(test_fragments, page_width)

    print(f"Column Boundaries: {column_boundaries}")
    print()

    # Test 1: Two consecutive full-width lines with small gap (should merge)
    print("Test 1: Two full-width lines with small gap")
    frag1 = test_fragments[0]
    frag2 = test_fragments[1]
    result = is_paragraph_break(frag1, frag2, 12.0, column_boundaries)
    print(f"  Fragment 1: left={frag1['left']}, width={frag1['width']}, right={frag1['left']+frag1['width']}")
    print(f"  Fragment 2: left={frag2['left']}, width={frag2['width']}, right={frag2['left']+frag2['width']}")
    print(f"  Should merge (return False): {not result}")
    print(f"  Result: {'✓ PASS - Lines merged' if not result else '✗ FAIL - Lines NOT merged'}")
    print()

    # Test 2: Full-width line followed by short line (should NOT merge)
    print("Test 2: Full-width line followed by short line")
    frag1 = test_fragments[1]
    frag2 = test_fragments[2]
    result = is_paragraph_break(frag1, frag2, 12.0, column_boundaries)
    print(f"  Fragment 1: left={frag1['left']}, width={frag1['width']}, right={frag1['left']+frag1['width']}")
    print(f"  Fragment 2: left={frag2['left']}, width={frag2['width']}, right={frag2['left']+frag2['width']}")
    print(f"  Should break (return True): {result}")
    print(f"  Result: {'✓ PASS - Lines NOT merged' if result else '✗ FAIL - Lines merged'}")
    print()

    # Test 3: Short line followed by full-width line (should NOT merge because prev line is short)
    print("Test 3: Short line followed by full-width line")
    frag1 = test_fragments[2]
    frag2 = test_fragments[3]
    result = is_paragraph_break(frag1, frag2, 12.0, column_boundaries)
    print(f"  Fragment 1: left={frag1['left']}, width={frag1['width']}, right={frag1['left']+frag1['width']}")
    print(f"  Fragment 2: left={frag2['left']}, width={frag2['width']}, right={frag2['left']+frag2['width']}")
    print(f"  Should break (return True): {result}")
    print(f"  Result: {'✓ PASS - Lines NOT merged' if result else '✗ FAIL - Lines merged'}")
    print()

    # Test 4: Large vertical gap (should break regardless)
    print("Test 4: Two full-width lines with large gap (>3px)")
    frag1 = test_fragments[3]
    frag2 = test_fragments[4]
    result = is_paragraph_break(frag1, frag2, 12.0, column_boundaries)
    vertical_gap = frag2['top'] - (frag1['top'] + frag1['height'])
    print(f"  Fragment 1: left={frag1['left']}, width={frag1['width']}")
    print(f"  Fragment 2: left={frag2['left']}, width={frag2['width']}")
    print(f"  Vertical gap: {vertical_gap}px")
    print(f"  Should break (return True): {result}")
    print(f"  Result: {'✓ PASS - Lines NOT merged' if result else '✗ FAIL - Lines merged'}")
    print()

    # Test 5: Fragment with indented next line (should NOT merge)
    print("Test 5: Full-width line followed by indented line")
    frag1 = {"left": 72, "width": 468, "top": 100, "height": 12, "col_id": 1, "text": "Full line", "reading_order_block": 1, "table_cell_id": ""}
    frag2 = {"left": 108, "width": 432, "top": 112, "height": 12, "col_id": 1, "text": "Indented line", "reading_order_block": 1, "table_cell_id": ""}
    result = is_paragraph_break(frag1, frag2, 12.0, column_boundaries)
    print(f"  Fragment 1: left={frag1['left']}, width={frag1['width']}")
    print(f"  Fragment 2: left={frag2['left']} (indented), width={frag2['width']}")
    print(f"  Should break (return True): {result}")
    print(f"  Result: {'✓ PASS - Lines NOT merged' if result else '✗ FAIL - Lines merged'}")
    print()

    print("=" * 70)
    print("All tests completed!")

if __name__ == "__main__":
    test_paragraph_break_logic()
