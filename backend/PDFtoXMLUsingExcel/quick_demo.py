#!/usr/bin/env python3
"""
Quick demonstration of the RittDoc Compliance Pipeline

This creates a simple test package and runs the full pipeline on it.
"""

import sys
import tempfile
import zipfile
from pathlib import Path
from lxml import etree

# Import the pipeline
from rittdoc_compliance_pipeline import RittDocCompliancePipeline


def create_test_package() -> Path:
    """Create a simple test DocBook XML package with some DTD violations"""
    
    print("Creating test package with intentional DTD violations...")
    
    # Create a DocBook structure with some violations
    book = etree.Element("book")
    book.set("id", "test-book")
    
    # Add bookinfo (but with missing required elements - will be auto-fixed)
    bookinfo = etree.SubElement(book, "bookinfo")
    title = etree.SubElement(bookinfo, "title")
    title.text = "Test Book for RittDoc Compliance"
    
    # Add a chapter with DTD violations
    chapter1 = etree.SubElement(book, "chapter")
    chapter1.set("id", "ch0001")
    
    ch1_title = etree.SubElement(chapter1, "title")
    ch1_title.text = "Chapter 1: Introduction"
    
    # VIOLATION 1: Direct para as child of chapter (should be in sect1)
    para1 = etree.SubElement(chapter1, "para")
    para1.text = "This paragraph is a direct child of chapter, which violates the DTD."
    
    # VIOLATION 2: Figure with no media content (will be removed)
    figure1 = etree.SubElement(chapter1, "figure")
    figure1.set("id", "fig-empty")
    fig_title = etree.SubElement(figure1, "title")
    fig_title.text = "Empty Figure"
    
    # Add a proper sect1 for comparison
    sect1 = etree.SubElement(chapter1, "sect1")
    sect1.set("id", "ch0001-sec01")
    
    sect1_title = etree.SubElement(sect1, "title")
    sect1_title.text = "Section 1.1"
    
    sect1_para = etree.SubElement(sect1, "para")
    sect1_para.text = "This is properly structured content within a sect1."
    
    # VIOLATION 3: Nested para (para inside para)
    outer_para = etree.SubElement(sect1, "para")
    outer_para.text = "This is an outer paragraph. "
    
    inner_para = etree.SubElement(outer_para, "para")
    inner_para.text = "This is an illegally nested paragraph."
    
    # Add chapter 2
    chapter2 = etree.SubElement(book, "chapter")
    chapter2.set("id", "ch0002")
    
    ch2_title = etree.SubElement(chapter2, "title")
    ch2_title.text = "Chapter 2: Methods"
    
    # More violations
    para2 = etree.SubElement(chapter2, "para")
    para2.text = "Another direct para under chapter."
    
    # Create temporary directory and files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Write Book.XML
        book_xml = tmp_path / "Book.XML"
        
        # Add DOCTYPE declaration
        doctype = '<!DOCTYPE book SYSTEM "RittDocBook.dtd">'
        xml_str = etree.tostring(book, encoding='unicode', pretty_print=True)
        full_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n{doctype}\n{xml_str}'
        
        book_xml.write_text(full_xml, encoding='utf-8')
        
        # Create separate chapter files (referenced by Book.XML)
        ch1_xml = tmp_path / "ch0001.xml"
        chapter1_str = etree.tostring(chapter1, encoding='unicode', pretty_print=True)
        ch1_xml.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n{chapter1_str}', encoding='utf-8')
        
        ch2_xml = tmp_path / "ch0002.xml"
        chapter2_str = etree.tostring(chapter2, encoding='unicode', pretty_print=True)
        ch2_xml.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n{chapter2_str}', encoding='utf-8')
        
        # Create ZIP package
        test_zip = Path("test_package.zip")
        with zipfile.ZipFile(test_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(book_xml, "Book.XML")
            zf.write(ch1_xml, "ch0001.xml")
            zf.write(ch2_xml, "ch0002.xml")
        
        print(f"✓ Created test package: {test_zip}")
        print(f"  - Book.XML (main file)")
        print(f"  - ch0001.xml (chapter 1 with violations)")
        print(f"  - ch0002.xml (chapter 2 with violations)")
        print()
        
        return test_zip


def main():
    """Run quick demonstration"""
    
    print("=" * 80)
    print("RITTDOC COMPLIANCE PIPELINE - QUICK DEMO")
    print("=" * 80)
    print()
    
    # Step 1: Create test package
    test_zip = create_test_package()
    
    # Step 2: Verify DTD exists
    dtd_path = Path("RITTDOCdtd/v1.1/RittDocBook.dtd")
    if not dtd_path.exists():
        print(f"Error: DTD not found at {dtd_path}")
        sys.exit(1)
    
    # Step 3: Run pipeline
    print("Starting compliance pipeline...")
    print()
    
    pipeline = RittDocCompliancePipeline(dtd_path)
    output_zip = Path("test_package_compliant.zip")
    
    try:
        success = pipeline.run(
            input_zip=test_zip,
            output_zip=output_zip,
            max_iterations=3
        )
        
        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        
        if success:
            print("\n✓ SUCCESS: Test package is now fully RittDoc DTD compliant!")
            print(f"\nGenerated files:")
            print(f"  - {output_zip} (compliant package)")
            
            # Check for validation report
            report = output_zip.parent / f"{output_zip.stem}_validation_report.xlsx"
            if report.exists():
                print(f"  - {report} (validation report)")
        else:
            print("\n⚠ PARTIAL SUCCESS: Some validation errors remain")
            print(f"\nGenerated files:")
            print(f"  - {output_zip} (improved package)")
            
            report = output_zip.parent / f"{output_zip.stem}_validation_report.xlsx"
            if report.exists():
                print(f"  - {report} (validation report with remaining errors)")
        
        # Cleanup
        if test_zip.exists():
            test_zip.unlink()
            print(f"\n✓ Cleaned up test package: {test_zip}")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
