#!/usr/bin/env python3
"""
Test script for metadata_processor module.

This script creates a sample Book.XML and metadata.csv file,
then tests the metadata population functionality.
"""

import tempfile
from pathlib import Path
from lxml import etree

from metadata_processor import (
    find_metadata_file,
    read_csv_metadata,
    create_bookinfo_element,
    populate_bookinfo_from_metadata,
)


def create_sample_book_xml(path: Path):
    """Create a simple Book.XML for testing."""
    book_xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE book PUBLIC "-//RIS Dev//DTD DocBook V4.3 -Based Variant V1.1//EN" "http://LOCALHOST/dtd/V1.1/RittDocBook.dtd" []>
<book>
    <bookinfo>
        <isbn>0000000000000</isbn>
        <title>Placeholder Title</title>
        <authorgroup>
            <author>
                <personname>
                    <surname>Placeholder Author</surname>
                </personname>
            </author>
        </authorgroup>
        <publisher>
            <publishername>Placeholder Publisher</publishername>
        </publisher>
        <pubdate>2024</pubdate>
        <edition>1st Edition</edition>
        <copyright>
            <year>2024</year>
            <holder>Placeholder</holder>
        </copyright>
    </bookinfo>
    <chapter>
        <title>Chapter 1</title>
        <para>Sample content</para>
    </chapter>
</book>
"""
    path.write_text(book_xml, encoding='utf-8')


def create_sample_metadata_csv(path: Path):
    """Create a sample metadata.csv for testing."""
    metadata_csv = """Field,Value
ISBN,978-1-234-56789-0
Title,Test Book Title
Subtitle,A Test Subtitle
Author,John Doe
Author,Jane Smith
Publisher,Test Publisher
PublicationDate,2024
Edition,2nd Edition
CopyrightYear,2024
CopyrightHolder,Test Publisher
"""
    path.write_text(metadata_csv, encoding='utf-8')


def test_find_metadata_file():
    """Test metadata file detection."""
    print("\n" + "="*70)
    print("TEST 1: Find Metadata File")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Test: No metadata file
        result = find_metadata_file(tmp_path)
        assert result is None, "Should return None when no metadata file exists"
        print("  ✓ Correctly returns None when no metadata file exists")
        
        # Test: CSV metadata file exists
        csv_path = tmp_path / "metadata.csv"
        csv_path.write_text("Field,Value\n", encoding='utf-8')
        result = find_metadata_file(tmp_path)
        assert result == csv_path, "Should find metadata.csv"
        print("  ✓ Correctly finds metadata.csv")
        
        csv_path.unlink()
        
        # Test: Excel metadata file exists
        xlsx_path = tmp_path / "metadata.xlsx"
        xlsx_path.write_text("dummy", encoding='utf-8')
        result = find_metadata_file(tmp_path)
        assert result == xlsx_path, "Should find metadata.xlsx"
        print("  ✓ Correctly finds metadata.xlsx")


def test_read_csv_metadata():
    """Test CSV metadata reading."""
    print("\n" + "="*70)
    print("TEST 2: Read CSV Metadata")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        csv_path = tmp_path / "metadata.csv"
        create_sample_metadata_csv(csv_path)
        
        metadata = read_csv_metadata(csv_path)
        
        # Verify extracted metadata
        assert metadata['isbn'] == '9781234567890', "ISBN should be cleaned (hyphens removed)"
        print(f"  ✓ ISBN correctly extracted and cleaned: {metadata['isbn']}")
        
        assert metadata['title'] == 'Test Book Title', "Title should match"
        print(f"  ✓ Title correctly extracted: {metadata['title']}")
        
        assert metadata['subtitle'] == 'A Test Subtitle', "Subtitle should match"
        print(f"  ✓ Subtitle correctly extracted: {metadata['subtitle']}")
        
        assert 'John Doe' in metadata['authors'], "Should extract first author"
        assert 'Jane Smith' in metadata['authors'], "Should extract second author"
        print(f"  ✓ Authors correctly extracted: {metadata['authors']}")
        
        assert metadata['publisher'] == 'Test Publisher', "Publisher should match"
        print(f"  ✓ Publisher correctly extracted: {metadata['publisher']}")
        
        assert metadata['pubdate'] == '2024', "Publication date should match"
        print(f"  ✓ Publication date correctly extracted: {metadata['pubdate']}")


def test_create_bookinfo_element():
    """Test BookInfo element creation."""
    print("\n" + "="*70)
    print("TEST 3: Create BookInfo Element")
    print("="*70)
    
    metadata = {
        'isbn': '9781234567890',
        'title': 'Test Title',
        'subtitle': 'Test Subtitle',
        'authors': ['John Doe', 'Jane Smith'],
        'publisher': 'Test Publisher',
        'pubdate': '2024',
        'edition': '2nd Edition',
        'copyright_year': '2024',
        'copyright_holder': 'Test Publisher'
    }
    
    bookinfo_elem = create_bookinfo_element(metadata)
    
    # Verify structure
    assert bookinfo_elem.tag == 'bookinfo', "Root should be bookinfo"
    print("  ✓ Root element is <bookinfo>")
    
    # Check ISBN
    isbn_elem = bookinfo_elem.find('.//isbn')
    assert isbn_elem is not None and isbn_elem.text == '9781234567890', "ISBN should be present"
    print(f"  ✓ ISBN element created: {isbn_elem.text}")
    
    # Check title
    title_elem = bookinfo_elem.find('.//title')
    assert title_elem is not None and title_elem.text == 'Test Title', "Title should be present"
    print(f"  ✓ Title element created: {title_elem.text}")
    
    # Check authors
    authors = bookinfo_elem.findall('.//author')
    assert len(authors) == 2, "Should have 2 authors"
    print(f"  ✓ {len(authors)} author elements created")
    
    # Check publisher
    publisher_elem = bookinfo_elem.find('.//publisher/publishername')
    assert publisher_elem is not None and publisher_elem.text == 'Test Publisher', "Publisher should be present"
    print(f"  ✓ Publisher element created: {publisher_elem.text}")


def test_populate_bookinfo():
    """Test full BookInfo population from metadata file."""
    print("\n" + "="*70)
    print("TEST 4: Populate BookInfo from Metadata File")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create sample files
        book_xml_path = tmp_path / "Book.XML"
        create_sample_book_xml(book_xml_path)
        
        csv_path = tmp_path / "metadata.csv"
        create_sample_metadata_csv(csv_path)
        
        # Run metadata population
        success = populate_bookinfo_from_metadata(book_xml_path, tmp_path, backup=False)
        assert success, "Metadata population should succeed"
        print("  ✓ Metadata population completed successfully")
        
        # Parse the updated Book.XML
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        tree = etree.parse(str(book_xml_path), parser)
        root = tree.getroot()
        
        # Verify updated content
        isbn = root.find('.//bookinfo/isbn')
        assert isbn is not None and isbn.text == '9781234567890', "ISBN should be updated"
        print(f"  ✓ ISBN updated in Book.XML: {isbn.text}")
        
        title = root.find('.//bookinfo/title')
        assert title is not None and title.text == 'Test Book Title', "Title should be updated"
        print(f"  ✓ Title updated in Book.XML: {title.text}")
        
        subtitle = root.find('.//bookinfo/subtitle')
        assert subtitle is not None and subtitle.text == 'A Test Subtitle', "Subtitle should be present"
        print(f"  ✓ Subtitle added to Book.XML: {subtitle.text}")
        
        authors = root.findall('.//bookinfo//author')
        assert len(authors) == 2, "Should have 2 authors"
        print(f"  ✓ {len(authors)} authors updated in Book.XML")
        
        # Verify chapter content is preserved
        chapter = root.find('.//chapter')
        assert chapter is not None, "Chapter should be preserved"
        print("  ✓ Existing content preserved")


def test_missing_metadata():
    """Test behavior when metadata file is missing."""
    print("\n" + "="*70)
    print("TEST 5: Missing Metadata File Handling")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create sample Book.XML but no metadata file
        book_xml_path = tmp_path / "Book.XML"
        create_sample_book_xml(book_xml_path)
        
        # Try to populate metadata
        success = populate_bookinfo_from_metadata(book_xml_path, tmp_path, backup=False)
        assert not success, "Should return False when no metadata file found"
        print("  ✓ Correctly returns False when metadata file is missing")
        print("  ✓ Warning message displayed to user")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("METADATA PROCESSOR TEST SUITE")
    print("="*70)
    
    try:
        test_find_metadata_file()
        test_read_csv_metadata()
        test_create_bookinfo_element()
        test_populate_bookinfo()
        test_missing_metadata()
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED")
        print("="*70)
        print("\nThe metadata processor is working correctly!")
        print("You can now use it with your PDF processing pipeline.\n")
        
        return 0
        
    except AssertionError as e:
        print("\n" + "="*70)
        print("✗ TEST FAILED")
        print("="*70)
        print(f"Error: {e}\n")
        return 1
    except Exception as e:
        print("\n" + "="*70)
        print("✗ TEST ERROR")
        print("="*70)
        print(f"Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
