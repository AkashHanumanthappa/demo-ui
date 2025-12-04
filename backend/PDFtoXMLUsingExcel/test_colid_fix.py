#!/usr/bin/env python3
"""
Test Suite for ColId Weaving Fix

Tests the improved ColId assignment logic against various scenarios:
- Single-column pages with mixed content
- Multi-column pages
- Edge cases
"""

import sys
from fix_colid_weaving import (
    is_single_column_page,
    smooth_colid_transitions,
    assign_single_column_ids,
    improved_assign_column_ids,
    analyze_colid_quality,
)


def create_test_fragments(left_widths, page_width=612.0):
    """
    Create test fragments from a list of (left, width) tuples.
    
    Args:
        left_widths: List of (left, width) tuples
        page_width: Page width
    
    Returns:
        List of fragment dictionaries
    """
    fragments = []
    for i, (left, width) in enumerate(left_widths):
        fragments.append({
            "left": left,
            "width": width,
            "baseline": 100 + i * 20,
            "top": 100 + i * 20,
            "height": 12,
            "col_id": None,
            "reading_order_index": i + 1,
            "text": f"Fragment {i+1}",
        })
    return fragments


def print_test_result(test_name, fragments, expected_colids):
    """Print test results with visual comparison."""
    actual_colids = [f["col_id"] for f in fragments]
    passed = actual_colids == expected_colids
    
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"\n{status} - {test_name}")
    print(f"  Expected: {expected_colids}")
    print(f"  Actual:   {actual_colids}")
    
    if not passed:
        print(f"  Difference:")
        for i, (exp, act) in enumerate(zip(expected_colids, actual_colids)):
            if exp != act:
                print(f"    Fragment {i+1}: expected {exp}, got {act}")
    
    # Show quality metrics
    metrics = analyze_colid_quality(fragments)
    print(f"  Weaving (0↔1 transitions): {metrics['weaving_01_count']}")
    print(f"  Total transitions: {metrics['transition_count']}")
    
    return passed


def test_single_column_short_headers():
    """Test single-column page with short headers and full paragraphs."""
    print("\n" + "="*70)
    print("TEST: Single-column page with short headers")
    print("="*70)
    
    # Page with:
    # - Short header (100px wide)
    # - Full paragraph (450px wide, >45% of 612)
    # - Indented paragraph (400px wide, <65% but >45%)
    # - Full paragraph (450px wide)
    
    page_width = 612.0
    col_starts = [72.0]  # Only one column detected
    
    fragments = create_test_fragments([
        (72, 100),   # Short header
        (72, 450),   # Full paragraph
        (108, 400),  # Indented paragraph
        (72, 450),   # Full paragraph
    ], page_width)
    
    print("\nBEFORE fix (original logic):")
    # Simulate original assignment
    for f in fragments:
        if f["width"] >= page_width * 0.45:
            f["col_id"] = 0
        else:
            f["col_id"] = 1
    
    before_metrics = analyze_colid_quality(fragments)
    print(f"  ColId sequence: {[f['col_id'] for f in fragments]}")
    print(f"  Weaving: {before_metrics['has_weaving']} ({before_metrics['weaving_01_count']} transitions)")
    
    # Reset and apply fix
    for f in fragments:
        f["col_id"] = None
    
    print("\nAFTER fix (improved logic):")
    improved_assign_column_ids(fragments, page_width, col_starts)
    
    # All should be ColId 1 (single column detected)
    expected = [1, 1, 1, 1]
    return print_test_result("Single-column detection", fragments, expected)


def test_multi_column_two_columns():
    """Test genuine two-column layout."""
    print("\n" + "="*70)
    print("TEST: Two-column layout")
    print("="*70)
    
    page_width = 612.0
    col_starts = [72.0, 340.0]  # Two columns detected
    
    # Page with:
    # - Full-width header spanning both columns
    # - Column 1 text
    # - Column 2 text
    # - Column 1 text
    # - Column 2 text
    
    fragments = create_test_fragments([
        (72, 500),   # Full-width header (spans both columns)
        (72, 250),   # Column 1
        (340, 250),  # Column 2
        (72, 250),   # Column 1
        (340, 250),  # Column 2
    ], page_width)
    
    improved_assign_column_ids(fragments, page_width, col_starts)
    
    # Should preserve multi-column structure
    # Full-width = 0, Col1 = 1, Col2 = 2
    expected = [0, 1, 2, 1, 2]
    return print_test_result("Two-column preservation", fragments, expected)


def test_smoothing_isolated_transitions():
    """Test smoothing of isolated ColId transitions."""
    print("\n" + "="*70)
    print("TEST: Smoothing isolated transitions")
    print("="*70)
    
    page_width = 612.0
    
    # Manually create fragments with ColId already assigned
    # Simulate a case where there are isolated transitions
    fragments = [
        {"left": 72, "width": 450, "baseline": 100, "reading_order_index": 1, "col_id": 0, "text": "F1"},
        {"left": 72, "width": 450, "baseline": 120, "reading_order_index": 2, "col_id": 0, "text": "F2"},
        {"left": 108, "width": 100, "baseline": 140, "reading_order_index": 3, "col_id": 1, "text": "F3"},  # Isolated
        {"left": 108, "width": 100, "baseline": 160, "reading_order_index": 4, "col_id": 1, "text": "F4"},  # Isolated
        {"left": 72, "width": 450, "baseline": 180, "reading_order_index": 5, "col_id": 0, "text": "F5"},
        {"left": 72, "width": 450, "baseline": 200, "reading_order_index": 6, "col_id": 0, "text": "F6"},
    ]
    
    print("\nBEFORE smoothing:")
    print(f"  ColId sequence: {[f['col_id'] for f in fragments]}")
    before_metrics = analyze_colid_quality(fragments)
    print(f"  Weaving: {before_metrics['has_weaving']} ({before_metrics['weaving_01_count']} transitions)")
    
    smooth_colid_transitions(fragments, min_group_size=3)
    
    print("\nAFTER smoothing:")
    # The isolated group of 2 (ColId 1) should be smoothed to ColId 0
    expected = [0, 0, 0, 0, 0, 0]
    return print_test_result("Smoothing isolated transitions", fragments, expected)


def test_single_column_detection_criteria():
    """Test the various criteria for single-column detection."""
    print("\n" + "="*70)
    print("TEST: Single-column detection criteria")
    print("="*70)
    
    page_width = 612.0
    
    # Test 1: Only one column start
    print("\n  Sub-test 1: One column start")
    col_starts_1 = [72.0]
    fragments_1 = create_test_fragments([(72, 200), (72, 300)], page_width)
    result_1 = is_single_column_page(fragments_1, col_starts_1, page_width)
    print(f"    Result: {result_1} (expected: True)")
    
    # Test 2: >80% left-aligned
    print("\n  Sub-test 2: >80% left-aligned to same position")
    col_starts_2 = [72.0, 340.0]  # Two starts detected (but it's actually single-column)
    fragments_2 = create_test_fragments([
        (72, 200), (72, 300), (72, 250), (72, 280), (72, 290),  # 5 at left=72
        (108, 200),  # 1 indented
    ], page_width)
    result_2 = is_single_column_page(fragments_2, col_starts_2, page_width)
    print(f"    Result: {result_2} (expected: True)")
    print(f"    Reason: {5}/{len(fragments_2)} = {5/len(fragments_2)*100:.0f}% left-aligned (>80%)")
    
    # Test 3: Weaving pattern (>5 transitions between 0 and 1)
    print("\n  Sub-test 3: Weaving pattern detection")
    col_starts_3 = [72.0, 340.0]
    fragments_3 = create_test_fragments([
        (72, 100), (72, 300), (72, 100), (72, 300),
        (72, 100), (72, 300), (72, 100), (72, 300),
    ], page_width)
    # Assign alternating ColIds (simulating weaving)
    for i, f in enumerate(fragments_3):
        f["col_id"] = 1 if f["width"] < 200 else 0
    result_3 = is_single_column_page(fragments_3, col_starts_3, page_width)
    print(f"    Result: {result_3} (expected: True)")
    metrics_3 = analyze_colid_quality(fragments_3)
    print(f"    Reason: {metrics_3['weaving_01_count']} transitions (>5)")
    
    all_pass = result_1 and result_2 and result_3
    print(f"\n  Overall: {'✓ PASS' if all_pass else '✗ FAIL'}")
    return all_pass


def test_edge_case_empty_page():
    """Test edge case: empty page."""
    print("\n" + "="*70)
    print("TEST: Edge case - empty page")
    print("="*70)
    
    fragments = []
    col_starts = []
    page_width = 612.0
    
    improved_assign_column_ids(fragments, page_width, col_starts)
    
    print(f"  Fragments: {len(fragments)}")
    print(f"  Result: No crash (✓ PASS)")
    return True


def test_integration_realistic_scenario():
    """Test realistic scenario with mixed content."""
    print("\n" + "="*70)
    print("TEST: Realistic scenario - Chapter page")
    print("="*70)
    
    page_width = 612.0
    col_starts = [72.0]  # Single column
    
    # Realistic chapter page:
    # - "Chapter 1" (short)
    # - "Introduction to the Topic" (medium)
    # - Full paragraph
    # - Indented quote
    # - Full paragraph
    # - Section header "Methods" (short)
    # - Full paragraph
    
    fragments = create_test_fragments([
        (72, 80),    # "Chapter 1"
        (72, 200),   # "Introduction to the Topic"
        (72, 480),   # Full paragraph
        (108, 420),  # Indented quote
        (72, 480),   # Full paragraph
        (72, 90),    # "Methods"
        (72, 480),   # Full paragraph
    ], page_width)
    
    print("\nBEFORE fix:")
    # Original logic
    for f in fragments:
        if f["width"] >= page_width * 0.45:
            f["col_id"] = 0
        else:
            f["col_id"] = 1
    
    before_seq = [f["col_id"] for f in fragments]
    before_metrics = analyze_colid_quality(fragments)
    print(f"  ColId sequence: {before_seq}")
    print(f"  Weaving: {before_metrics['has_weaving']} ({before_metrics['weaving_01_count']} transitions)")
    
    # Reset
    for f in fragments:
        f["col_id"] = None
    
    print("\nAFTER fix:")
    improved_assign_column_ids(fragments, page_width, col_starts)
    
    # All should be ColId 1
    expected = [1, 1, 1, 1, 1, 1, 1]
    return print_test_result("Realistic chapter page", fragments, expected)


def run_all_tests():
    """Run all test cases and report results."""
    print("\n" + "="*70)
    print("COLID WEAVING FIX - TEST SUITE")
    print("="*70)
    
    tests = [
        ("Single-column with short headers", test_single_column_short_headers),
        ("Two-column layout preservation", test_multi_column_two_columns),
        ("Smoothing isolated transitions", test_smoothing_isolated_transitions),
        ("Single-column detection criteria", test_single_column_detection_criteria),
        ("Edge case: empty page", test_edge_case_empty_page),
        ("Realistic scenario", test_integration_realistic_scenario),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
