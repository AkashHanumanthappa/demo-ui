#!/usr/bin/env python3
"""
Test script to verify the TOC.xml font size fix.

This script creates a minimal test case to ensure that:
1. Font sizes are correctly looked up from font_info_map
2. TOC.xml entries have non-zero font sizes
3. The fix doesn't break the existing functionality
"""

import xml.etree.ElementTree as ET
import tempfile
import os
from font_roles_auto import extract_toc_section, _f


def create_test_unified_xml():
    """Create a minimal unified XML with fontspec and text elements."""
    root = ET.Element("document", {"source": "test.pdf"})
    
    # Add fontspec elements (font definitions)
    fontspec1 = ET.SubElement(root, "fontspec", {
        "id": "0",
        "size": "12",
        "family": "TimesNewRoman",
        "color": "#000000"
    })
    
    fontspec2 = ET.SubElement(root, "fontspec", {
        "id": "1",
        "size": "14",
        "family": "TimesNewRoman-Bold",
        "color": "#000000"
    })
    
    fontspec3 = ET.SubElement(root, "fontspec", {
        "id": "2",
        "size": "10",
        "family": "Arial",
        "color": "#000000"
    })
    
    # Page 1 - Contains "Table of Contents" heading
    page1 = ET.SubElement(root, "page", {
        "number": "1",
        "width": "612",
        "height": "792"
    })
    texts1 = ET.SubElement(page1, "texts")
    para1 = ET.SubElement(texts1, "para", {"col_id": "0", "reading_block": "1"})
    
    # TOC heading (font 1 = size 14)
    text1 = ET.SubElement(para1, "text", {
        "font": "1",
        "reading_order": "1",
        "row_index": "1",
        "baseline": "100",
        "left": "72",
        "top": "72",
        "width": "200",
        "height": "14"
    })
    text1.text = "Table of Contents"
    
    # Page 2 - Contains TOC entries
    page2 = ET.SubElement(root, "page", {
        "number": "2",
        "width": "612",
        "height": "792"
    })
    texts2 = ET.SubElement(page2, "texts")
    para2 = ET.SubElement(texts2, "para", {"col_id": "0", "reading_block": "1"})
    
    # TOC entry 1 (font 0 = size 12)
    text2 = ET.SubElement(para2, "text", {
        "font": "0",
        "reading_order": "2",
        "row_index": "2",
        "baseline": "150",
        "left": "72",
        "top": "150",
        "width": "300",
        "height": "12"
    })
    text2.text = "Chapter 1: Introduction ................. 1"
    
    # TOC entry 2 (font 0 = size 12)
    text3 = ET.SubElement(para2, "text", {
        "font": "0",
        "reading_order": "3",
        "row_index": "3",
        "baseline": "175",
        "left": "72",
        "top": "175",
        "width": "300",
        "height": "12"
    })
    text3.text = "Chapter 2: Methods ..................... 15"
    
    # Page 3 - Contains a chapter heading (should stop TOC extraction)
    page3 = ET.SubElement(root, "page", {
        "number": "3",
        "width": "612",
        "height": "792"
    })
    texts3 = ET.SubElement(page3, "texts")
    para3 = ET.SubElement(texts3, "para", {"col_id": "0", "reading_block": "1"})
    
    # Chapter heading (font 1 = size 14, same as TOC heading)
    text4 = ET.SubElement(para3, "text", {
        "font": "1",
        "reading_order": "4",
        "row_index": "4",
        "baseline": "100",
        "left": "72",
        "top": "100",
        "width": "200",
        "height": "14"
    })
    text4.text = "Chapter 1: Introduction"
    
    return root


def build_font_info_map(root):
    """Build font_info_map from fontspec elements (same logic as font_roles_auto.py)."""
    font_info_map = {}
    
    for fs in root.findall(".//fontspec"):
        fid = fs.get("id")
        size_attr = fs.get("size")
        family_attr = fs.get("family") or fs.get("name", "")
        color_attr = fs.get("color", "")
        
        size_val = _f(size_attr)
        if fid is not None and size_val and not (isinstance(size_val, float) and size_val != size_val):  # Check for NaN
            font_info_map[fid] = {
                "size": round(size_val, 2),
                "family": family_attr,
                "color": color_attr
            }
    
    return font_info_map


def test_toc_extraction():
    """Test that TOC extraction correctly uses font sizes from font_info_map."""
    print("="*70)
    print("Testing TOC.xml Font Size Fix")
    print("="*70)
    
    # Create test data
    print("\n1. Creating test unified XML...")
    root = create_test_unified_xml()
    
    # Build font info map
    print("2. Building font_info_map from fontspec elements...")
    font_info_map = build_font_info_map(root)
    print(f"   Font info map: {font_info_map}")
    
    # Create temporary output file
    with tempfile.NamedTemporaryFile(mode='w', suffix='_TOC.xml', delete=False) as tmp:
        toc_output_path = tmp.name
    
    try:
        # Extract TOC
        print("\n3. Extracting TOC section...")
        toc_info = extract_toc_section(
            root=root,
            toc_start_size=14.0,  # Size of "Table of Contents" heading
            toc_start_page=1,
            output_path=toc_output_path,
            font_info_map=font_info_map
        )
        
        print(f"   TOC extraction info:")
        print(f"     - Start page: {toc_info['start_page']}")
        print(f"     - End page: {toc_info['end_page']}")
        print(f"     - Entry count: {toc_info['entry_count']}")
        print(f"     - End reason: {toc_info['end_reason']}")
        
        # Parse the generated TOC.xml
        print("\n4. Verifying generated TOC.xml...")
        toc_tree = ET.parse(toc_output_path)
        toc_root = toc_tree.getroot()
        
        # Check all entries have non-zero font sizes
        all_entries = toc_root.findall(".//entry")
        print(f"   Found {len(all_entries)} entries in TOC.xml")
        
        success = True
        for i, entry in enumerate(all_entries):
            size = entry.get("size", "0")
            family = entry.get("family", "Unknown")
            text = entry.text or ""
            
            print(f"   Entry {i+1}: size={size}, family={family}, text='{text[:50]}'")
            
            # Verify size is non-zero
            size_val = float(size)
            if size_val == 0:
                print(f"     ❌ ERROR: Font size is 0!")
                success = False
            else:
                print(f"     ✓ Font size is correct")
        
        # Verify boundary detection worked
        if toc_info['end_page'] == 3 and 'found_heading' in toc_info['end_reason']:
            print("\n   ✓ TOC extraction stopped at correct boundary (page 3, chapter heading)")
        else:
            print(f"\n   ⚠ Warning: TOC extraction may not have stopped correctly")
            print(f"     Expected: end_page=3, end_reason contains 'found_heading'")
            print(f"     Got: end_page={toc_info['end_page']}, end_reason={toc_info['end_reason']}")
        
        print("\n" + "="*70)
        if success:
            print("✓ TEST PASSED: All TOC entries have correct font sizes")
        else:
            print("❌ TEST FAILED: Some entries have incorrect font sizes")
        print("="*70)
        
        return success
        
    finally:
        # Clean up
        if os.path.exists(toc_output_path):
            os.unlink(toc_output_path)


if __name__ == "__main__":
    import sys
    success = test_toc_extraction()
    sys.exit(0 if success else 1)
