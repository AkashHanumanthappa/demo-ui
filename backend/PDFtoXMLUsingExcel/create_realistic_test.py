#!/usr/bin/env python3
"""
Create a realistic test package with entity references and DTD violations
"""

import sys
import tempfile
import zipfile
from pathlib import Path
from lxml import etree


def create_realistic_package() -> Path:
    """Create a realistic DocBook package with entity references and DTD violations"""
    
    print("Creating realistic test package with entity references...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create chapter 1 with violations
        chapter1 = etree.Element("chapter")
        chapter1.set("id", "ch0001")
        
        ch1_title = etree.SubElement(chapter1, "title")
        ch1_title.text = "Chapter 1: Introduction"
        
        # VIOLATION 1: Direct para as child of chapter
        para1 = etree.SubElement(chapter1, "para")
        para1.text = "This paragraph violates DTD - should be in sect1."
        
        # VIOLATION 2: Empty figure
        figure1 = etree.SubElement(chapter1, "figure")
        figure1.set("id", "fig-empty")
        fig_title = etree.SubElement(figure1, "title")
        fig_title.text = "Empty Figure (will be removed)"
        
        # Add a proper sect1 
        sect1 = etree.SubElement(chapter1, "sect1")
        sect1.set("id", "ch0001-sec01")
        
        sect1_title = etree.SubElement(sect1, "title")
        sect1_title.text = "Section 1.1"
        
        sect1_para = etree.SubElement(sect1, "para")
        sect1_para.text = "This is proper content."
        
        # VIOLATION 3: Nested para
        outer_para = etree.SubElement(sect1, "para")
        outer_para.text = "Outer paragraph. "
        inner_para = etree.SubElement(outer_para, "para")
        inner_para.text = "Nested para (violation)."
        
        # Write ch0001.xml
        ch1_xml = tmp_path / "ch0001.xml"
        ch1_str = etree.tostring(chapter1, encoding='unicode', pretty_print=True)
        ch1_xml.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n{ch1_str}', encoding='utf-8')
        
        # Create chapter 2 with violations
        chapter2 = etree.Element("chapter")
        chapter2.set("id", "ch0002")
        
        ch2_title = etree.SubElement(chapter2, "title")
        ch2_title.text = "Chapter 2: Methods"
        
        # VIOLATION: Another direct para
        para2 = etree.SubElement(chapter2, "para")
        para2.text = "Another direct para violation."
        
        # VIOLATION: Figure with table in it (not allowed)
        figure2 = etree.SubElement(chapter2, "figure")
        figure2.set("id", "fig-table")
        fig2_title = etree.SubElement(figure2, "title")
        fig2_title.text = "Table 1: Data"
        
        table = etree.SubElement(figure2, "table")
        table_title = etree.SubElement(table, "title")
        table_title.text = "Sample Table"
        
        # Write ch0002.xml
        ch2_xml = tmp_path / "ch0002.xml"
        ch2_str = etree.tostring(chapter2, encoding='unicode', pretty_print=True)
        ch2_xml.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n{ch2_str}', encoding='utf-8')
        
        # Create Book.XML with entity references
        book_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE book SYSTEM "RittDocBook.dtd" [
<!ENTITY ch0001 SYSTEM "ch0001.xml">
<!ENTITY ch0002 SYSTEM "ch0002.xml">
]>
<book id="test-book">
  <bookinfo>
    <title>Realistic Test Book</title>
    <author>
      <personname>
        <firstname>Test</firstname>
        <surname>Author</surname>
      </personname>
    </author>
    <publisher>
      <publishername>Test Publisher</publishername>
    </publisher>
    <isbn>1234567890123</isbn>
    <pubdate>2024</pubdate>
    <copyright>
      <year>2024</year>
      <holder>Test Copyright Holder</holder>
    </copyright>
  </bookinfo>
  &ch0001;
  &ch0002;
</book>
'''
        
        book_xml = tmp_path / "Book.XML"
        book_xml.write_text(book_xml_content, encoding='utf-8')
        
        # Create ZIP package
        test_zip = Path("realistic_test_package.zip")
        with zipfile.ZipFile(test_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(book_xml, "Book.XML")
            zf.write(ch1_xml, "ch0001.xml")
            zf.write(ch2_xml, "ch0002.xml")
        
        print(f"✓ Created realistic test package: {test_zip}")
        print(f"  - Book.XML (with entity references)")
        print(f"  - ch0001.xml (chapter 1 with violations)")
        print(f"  - ch0002.xml (chapter 2 with violations)")
        print()
        
        return test_zip


def main():
    """Create realistic test and run pipeline"""
    from rittdoc_compliance_pipeline import RittDocCompliancePipeline
    
    print("=" * 80)
    print("REALISTIC TEST - RITTDOC COMPLIANCE PIPELINE")
    print("=" * 80)
    print()
    
    # Create test package
    test_zip = create_realistic_package()
    
    # Verify DTD exists
    dtd_path = Path("RITTDOCdtd/v1.1/RittDocBook.dtd")
    if not dtd_path.exists():
        print(f"Error: DTD not found at {dtd_path}")
        sys.exit(1)
    
    # Run pipeline
    print("Starting compliance pipeline on realistic test package...")
    print()
    
    pipeline = RittDocCompliancePipeline(dtd_path)
    output_zip = Path("realistic_test_compliant.zip")
    
    try:
        success = pipeline.run(
            input_zip=test_zip,
            output_zip=output_zip,
            max_iterations=3
        )
        
        print("\n" + "=" * 80)
        print("REALISTIC TEST COMPLETE")
        print("=" * 80)
        
        if success:
            print("\n✓ SUCCESS: Package is now fully RittDoc DTD compliant!")
        else:
            print("\n⚠ PARTIAL SUCCESS: Some validation errors remain")
        
        print(f"\nGenerated files:")
        print(f"  Input:  {test_zip}")
        print(f"  Output: {output_zip}")
        
        report = output_zip.parent / f"{output_zip.stem}_validation_report.xlsx"
        if report.exists():
            print(f"  Report: {report}")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
