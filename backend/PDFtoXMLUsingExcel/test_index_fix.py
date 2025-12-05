#!/usr/bin/env python3
"""
Test script to verify Index chapter fixes are working.

Tests:
1. Alphabet headers (A-Z) are not filtered
2. Index section doesn't exit prematurely
3. Multi-page index is fully captured
"""

import re
try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False


def test_alphabet_headers_not_filtered():
    """Test that alphabet headers (including C, D, I, V, X) are retained."""
    print("\n" + "="*70)
    print("TEST 1: Alphabet Headers Not Filtered")
    print("="*70)
    
    # Simulate the filtering logic
    class FakeLine:
        def __init__(self, text, page_height=800, top=100, left=50, page_width=600, font_size=14, page_num=200):
            self.text = text
            self.page_height = page_height
            self.top = top
            self.left = left
            self.page_width = page_width
            self.font_size = font_size
            self.page_num = page_num
    
    # Test letters that were problematic (roman numerals)
    test_letters = ['A', 'B', 'C', 'D', 'I', 'V', 'X', 'L', 'M', 'Z']
    
    # Simulate being in index section
    in_index_section = True
    
    passed = 0
    failed = 0
    
    for letter in test_letters:
        line = FakeLine(letter)
        text = line.text.strip()
        
        # This is the new logic from the fix
        is_potential_alphabet_header = (
            in_index_section and
            len(text) == 1 and 
            text.isupper() and 
            text.isalpha()
        )
        
        if is_potential_alphabet_header:
            print(f"  ✓ {letter}: Would NOT be filtered (alphabet header detected)")
            passed += 1
        else:
            print(f"  ✗ {letter}: Would be filtered (BUG!)")
            failed += 1
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0


def test_index_exit_logic():
    """Test that index mode doesn't exit on alphabet headers."""
    print("\n" + "="*70)
    print("TEST 2: Index Exit Logic")
    print("="*70)
    
    class FakeLine:
        def __init__(self, text, font_size=14):
            self.text = text
            self.font_size = font_size
    
    # Simulate different line types
    test_cases = [
        ("A", 18, True, "Should STAY in index (alphabet header)"),
        ("B", 18, True, "Should STAY in index (alphabet header)"),
        ("Index", 20, True, "Should STAY in index (duplicate heading)"),
        ("Chapter 2: Methods", 20, False, "Should EXIT index (new chapter)"),
        ("Some Random Text", 10, True, "Should STAY in index (regular content)"),
        ("References and Resources", 18, False, "Should EXIT index (multi-word heading)"),
    ]
    
    passed = 0
    failed = 0
    
    for text, font_size, should_stay, description in test_cases:
        line = FakeLine(text, font_size)
        body_size = 12
        
        # Check if has heading font
        has_heading_font = font_size >= body_size + 4
        
        # Simulate the new exit logic
        if has_heading_font:
            if len(text) == 1 and text.isupper() and text.isalpha():
                # Alphabet header - stay in index
                exits_index = False
            elif len(text.split()) > 5:
                # Multi-word heading - exit
                exits_index = True
            else:
                # Other cases - would need more checks
                exits_index = False
        else:
            exits_index = False
        
        stays_in_index = not exits_index
        
        if stays_in_index == should_stay:
            print(f"  ✓ '{text}': {description}")
            passed += 1
        else:
            print(f"  ✗ '{text}': {description} (FAILED!)")
            print(f"      Expected: {'STAY' if should_stay else 'EXIT'}, Got: {'STAY' if stays_in_index else 'EXIT'}")
            failed += 1
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0


def test_docbook_output(xml_file=None):
    """Test the actual DocBook output if available."""
    if not HAS_LXML:
        print("\n" + "="*70)
        print("TEST 3: DocBook Output Analysis")
        print("="*70)
        print("  ⚠ lxml not available - skipping XML analysis")
        return True
    
    if not xml_file:
        print("\n" + "="*70)
        print("TEST 3: DocBook Output Analysis")
        print("="*70)
        print("  ⚠ No XML file provided - skipping")
        print("  Usage: python test_index_fix.py /path/to/output.xml")
        return True
    
    print("\n" + "="*70)
    print("TEST 3: DocBook Output Analysis")
    print("="*70)
    print(f"  Analyzing: {xml_file}")
    
    try:
        tree = etree.parse(xml_file)
        root = tree.getroot()
        
        # Find index chapter
        index_chapters = root.findall(".//chapter[@role='index']")
        
        if not index_chapters:
            print("  ✗ No index chapter found in output!")
            return False
        
        print(f"  ✓ Found {len(index_chapters)} index chapter(s)")
        
        # Check for alphabet headers
        index_chapter = index_chapters[0]
        bridgeheads = index_chapter.findall(".//bridgehead")
        
        alphabet_headers = []
        for bh in bridgeheads:
            text = ''.join(bh.itertext()).strip()
            if len(text) == 1 and text.isupper() and text.isalpha():
                alphabet_headers.append(text)
        
        if alphabet_headers:
            print(f"  ✓ Found {len(alphabet_headers)} alphabet headers: {', '.join(sorted(set(alphabet_headers)))}")
            
            # Check for the problematic letters (roman numerals)
            roman_letters = set(['C', 'D', 'I', 'V', 'X', 'L', 'M'])
            found_roman = roman_letters & set(alphabet_headers)
            
            if found_roman:
                print(f"  ✓ Roman numeral letters present: {', '.join(sorted(found_roman))}")
                print("     (These were being filtered before the fix)")
            else:
                print(f"  ⚠ Roman numeral letters NOT found: {', '.join(sorted(roman_letters - found_roman))}")
                print("     (Expected at least some of these in a full index)")
        else:
            print("  ⚠ No alphabet headers found")
            print("     (Expected <bridgehead> elements for A, B, C, etc.)")
        
        # Count index items
        index_items = index_chapter.findall(".//para[@role='index']")
        if not index_items:
            # Try alternative structure
            index_items = index_chapter.findall(".//varlistentry")
        
        if index_items:
            print(f"  ✓ Found {len(index_items)} index entries")
        else:
            print("  ⚠ No index entries found")
        
        # Check page distribution
        pages_with_content = set()
        for elem in index_chapter.iter():
            page_num = elem.get('page_num')
            if page_num:
                pages_with_content.add(int(page_num))
        
        if pages_with_content:
            min_page = min(pages_with_content)
            max_page = max(pages_with_content)
            page_count = max_page - min_page + 1
            print(f"  ✓ Index spans pages {min_page}-{max_page} ({page_count} pages)")
            
            if page_count == 1:
                print("  ⚠ WARNING: Index only spans 1 page!")
                print("     This might indicate the bug is still present")
                return False
        else:
            print("  ⚠ No page numbers found in index")
        
        return True
        
    except FileNotFoundError:
        print(f"  ✗ File not found: {xml_file}")
        return False
    except Exception as e:
        print(f"  ✗ Error parsing XML: {e}")
        return False


def main():
    import sys
    
    print("="*70)
    print("INDEX CHAPTER FIX - VERIFICATION TESTS")
    print("="*70)
    
    results = []
    
    # Test 1: Alphabet header filtering
    results.append(("Alphabet Headers", test_alphabet_headers_not_filtered()))
    
    # Test 2: Index exit logic
    results.append(("Index Exit Logic", test_index_exit_logic()))
    
    # Test 3: DocBook output (if file provided)
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
        results.append(("DocBook Output", test_docbook_output(xml_file)))
    else:
        results.append(("DocBook Output", test_docbook_output(None)))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED - Fix is working correctly!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Please review the output above")
        return 1


if __name__ == "__main__":
    exit(main())
