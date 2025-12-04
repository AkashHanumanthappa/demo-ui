#!/usr/bin/env python3
"""
Test to verify that narrow continuation lines in the footnote zone
inherit their parent's col_id=0 assignment.
"""

from pdf_to_excel_columns import group_col0_by_vertical_gap

def test_footnote_zone_continuation():
    """
    Test that narrow continuation lines in the footnote zone get col_id=0
    even though they're narrower than the 40% threshold.
    """
    print("Testing footnote zone continuation line grouping...")
    
    # Simulate page 1010 scenario
    page_width = 823.0
    page_height = 1161.0
    typical_line_height = 15.0
    footnote_threshold = page_height * 0.75  # 870.75
    
    # Create mock fragments similar to references 20-22
    fragments = [
        # Reference 19 (col_id=1, above footnote zone)
        {"top": 851, "height": 15, "baseline": 866, "width": 601, "col_id": 1},
        
        # Reference 20 - first line (wide, gets col_id=0 from footnote reclassification)
        {"top": 906, "height": 15, "baseline": 921, "width": 594, "col_id": 0},
        
        # Reference 20 - continuation (wide)
        {"top": 923, "height": 15, "baseline": 938, "width": 571, "col_id": 0},
        
        # Reference 20 - last line (NARROW - should inherit col_id=0)
        {"top": 939, "height": 15, "baseline": 954, "width": 120, "col_id": 1},  # Currently wrong!
        
        # Reference 21 - first line (wide)
        {"top": 962, "height": 15, "baseline": 977, "width": 598, "col_id": 0},
        
        # Reference 21 - continuation (wide)
        {"top": 978, "height": 15, "baseline": 993, "width": 567, "col_id": 0},
        
        # Reference 21 - continuation (wide)
        {"top": 994, "height": 15, "baseline": 1009, "width": 520, "col_id": 0},
        
        # Reference 22 - first line (wide)
        {"top": 1017, "height": 15, "baseline": 1032, "width": 598, "col_id": 0},
        
        # Reference 22 - last line (NARROW - should inherit col_id=0)
        {"top": 1033, "height": 15, "baseline": 1048, "width": 314, "col_id": 1},  # Currently wrong!
    ]
    
    print("\nBEFORE grouping:")
    for i, frag in enumerate(fragments):
        in_zone = "📍 IN FOOTNOTE ZONE" if frag["top"] >= footnote_threshold else ""
        print(f"  Fragment {i}: top={frag['top']:4.0f}, width={frag['width']:3.0f}, col_id={frag['col_id']} {in_zone}")
    
    # Apply the fix
    group_col0_by_vertical_gap(fragments, typical_line_height, page_width=page_width, page_height=page_height)
    
    print("\nAFTER grouping:")
    for i, frag in enumerate(fragments):
        in_zone = "📍 IN FOOTNOTE ZONE" if frag["top"] >= footnote_threshold else ""
        status = "✅" if frag["top"] >= footnote_threshold and frag["col_id"] == 0 else ""
        print(f"  Fragment {i}: top={frag['top']:4.0f}, width={frag['width']:3.0f}, col_id={frag['col_id']} {status} {in_zone}")
    
    # Verify the fix worked
    print("\n" + "="*70)
    print("VERIFICATION:")
    print("="*70)
    
    # Check that narrow fragment at top=939 now has col_id=0
    frag_939 = [f for f in fragments if f["top"] == 939][0]
    if frag_939["col_id"] == 0:
        print("✅ PASS: Narrow fragment at top=939 (width=120) correctly has col_id=0")
    else:
        print("❌ FAIL: Narrow fragment at top=939 still has col_id=1")
        return False
    
    # Check that narrow fragment at top=1033 now has col_id=0
    frag_1033 = [f for f in fragments if f["top"] == 1033][0]
    if frag_1033["col_id"] == 0:
        print("✅ PASS: Narrow fragment at top=1033 (width=314) correctly has col_id=0")
    else:
        print("❌ FAIL: Narrow fragment at top=1033 still has col_id=1")
        return False
    
    # Check that all fragments in footnote zone have col_id=0
    footnote_frags = [f for f in fragments if f["top"] >= footnote_threshold]
    all_col0 = all(f["col_id"] == 0 for f in footnote_frags)
    if all_col0:
        print(f"✅ PASS: All {len(footnote_frags)} fragments in footnote zone have col_id=0")
    else:
        print(f"❌ FAIL: Some fragments in footnote zone don't have col_id=0")
        return False
    
    # Check that fragment above footnote zone kept col_id=1
    frag_851 = [f for f in fragments if f["top"] == 851][0]
    if frag_851["col_id"] == 1:
        print("✅ PASS: Fragment above footnote zone (top=851) correctly kept col_id=1")
    else:
        print("❌ FAIL: Fragment above footnote zone incorrectly changed to col_id=0")
        return False
    
    print("\n" + "="*70)
    print("🎉 ALL TESTS PASSED!")
    print("="*70)
    print("\nThe fix correctly:")
    print("  1. Groups narrow continuation lines with their wide parent references")
    print("  2. Only applies this logic in the footnote zone (bottom 25% of page)")
    print("  3. Preserves col_id=1 for content above the footnote zone")
    return True


if __name__ == "__main__":
    test_footnote_zone_continuation()
