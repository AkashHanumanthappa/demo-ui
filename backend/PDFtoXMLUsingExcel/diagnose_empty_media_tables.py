#!/usr/bin/env python3
"""
Diagnostic script to analyze empty <media /> and <tables /> tags in unified XML.

This script helps identify:
1. Why <media /> and <tables /> tags are empty in _unified.xml
2. Which images from MultiMedia.xml are getting transferred to chapter XMLs
3. Where the disconnect occurs in the pipeline
"""

import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from collections import defaultdict

def analyze_multimedia_xml(multimedia_xml_path):
    """Analyze MultiMedia.xml to see what media/tables are available."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {multimedia_xml_path}")
    print(f"{'='*70}")
    
    if not Path(multimedia_xml_path).exists():
        print(f"❌ File not found: {multimedia_xml_path}")
        return None
    
    try:
        tree = ET.parse(multimedia_xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
        return None
    
    # Count media and tables per page
    pages_data = {}
    total_media = 0
    total_tables = 0
    
    for page_elem in root.findall('.//page'):
        page_num = page_elem.get('index', 'unknown')
        
        # Count media elements
        media_elements = page_elem.findall('media')
        tables_elements = page_elem.findall('table')
        
        total_media += len(media_elements)
        total_tables += len(tables_elements)
        
        if media_elements or tables_elements:
            pages_data[page_num] = {
                'media_count': len(media_elements),
                'table_count': len(tables_elements),
                'media_ids': [m.get('id', 'no-id') for m in media_elements],
                'table_ids': [t.get('id', 'no-id') for t in tables_elements],
            }
    
    print(f"\n📊 MultiMedia.xml Summary:")
    print(f"  Total pages with media/tables: {len(pages_data)}")
    print(f"  Total <media> elements: {total_media}")
    print(f"  Total <table> elements: {total_tables}")
    
    # Show sample of first few pages
    print(f"\n📄 Sample (first 5 pages):")
    for i, (page_num, data) in enumerate(list(pages_data.items())[:5]):
        print(f"  Page {page_num}: {data['media_count']} media, {data['table_count']} tables")
        if data['media_ids']:
            print(f"    Media IDs: {', '.join(data['media_ids'][:3])}")
        if data['table_ids']:
            print(f"    Table IDs: {', '.join(data['table_ids'][:3])}")
    
    return {
        'total_media': total_media,
        'total_tables': total_tables,
        'pages_data': pages_data
    }


def analyze_unified_xml(unified_xml_path):
    """Analyze _unified.xml to see what media/tables were transferred."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {unified_xml_path}")
    print(f"{'='*70}")
    
    if not Path(unified_xml_path).exists():
        print(f"❌ File not found: {unified_xml_path}")
        return None
    
    try:
        tree = ET.parse(unified_xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
        return None
    
    # Count empty vs non-empty media/table tags
    pages_data = {}
    total_media_tags = 0
    empty_media_tags = 0
    total_table_tags = 0
    empty_table_tags = 0
    
    for page_elem in root.findall('.//page'):
        page_num = page_elem.get('number', 'unknown')
        
        # Find <media> wrapper element (not individual media elements)
        media_wrapper = page_elem.find('media')
        tables_wrapper = page_elem.find('tables')
        
        media_count = 0
        table_count = 0
        
        if media_wrapper is not None:
            # Count actual <media> elements inside the wrapper
            media_elements = media_wrapper.findall('media')
            media_count = len(media_elements)
            total_media_tags += media_count
            
            # Check if wrapper is empty
            if media_count == 0:
                empty_media_tags += 1
        
        if tables_wrapper is not None:
            # Count actual <table> elements inside the wrapper
            table_elements = tables_wrapper.findall('table')
            table_count = len(table_elements)
            total_table_tags += table_count
            
            # Check if wrapper is empty
            if table_count == 0:
                empty_table_tags += 1
        
        if media_count > 0 or table_count > 0:
            pages_data[page_num] = {
                'media_count': media_count,
                'table_count': table_count,
            }
    
    # Count pages with empty wrappers
    total_pages = len(root.findall('.//page'))
    pages_with_empty_media = empty_media_tags
    pages_with_empty_tables = empty_table_tags
    
    print(f"\n📊 Unified XML Summary:")
    print(f"  Total pages: {total_pages}")
    print(f"  Total <media> elements (within <media> wrappers): {total_media_tags}")
    print(f"  Total <table> elements (within <tables> wrappers): {total_table_tags}")
    print(f"  Pages with EMPTY <media> wrappers: {pages_with_empty_media}")
    print(f"  Pages with EMPTY <tables> wrappers: {pages_with_empty_tables}")
    
    # Show sample of pages with content
    if pages_data:
        print(f"\n📄 Sample pages WITH media/tables (first 5):")
        for i, (page_num, data) in enumerate(list(pages_data.items())[:5]):
            print(f"  Page {page_num}: {data['media_count']} media, {data['table_count']} tables")
    
    return {
        'total_media': total_media_tags,
        'total_tables': total_table_tags,
        'pages_with_empty_media': pages_with_empty_media,
        'pages_with_empty_tables': pages_with_empty_tables,
        'pages_data': pages_data
    }


def check_package_zip(package_zip_path):
    """Check what's inside the package ZIP file."""
    print(f"\n{'='*70}")
    print(f"ANALYZING PACKAGE: {package_zip_path}")
    print(f"{'='*70}")
    
    import zipfile
    
    if not Path(package_zip_path).exists():
        print(f"❌ File not found: {package_zip_path}")
        return None
    
    try:
        with zipfile.ZipFile(package_zip_path, 'r') as zf:
            file_list = zf.namelist()
            
            # Count different types of files
            multimedia_files = [f for f in file_list if f.startswith('MultiMedia/') and f.endswith(('.png', '.jpg', '.jpeg'))]
            chapter_files = [f for f in file_list if f.endswith('.xml') and f != 'Book.XML']
            
            print(f"\n📦 Package Contents:")
            print(f"  Total files: {len(file_list)}")
            print(f"  Chapter XMLs: {len(chapter_files)}")
            print(f"  MultiMedia files: {len(multimedia_files)}")
            
            # Analyze chapter XMLs for media references
            print(f"\n🔍 Analyzing chapter XMLs for media references...")
            total_media_refs = 0
            total_table_refs = 0
            
            for chapter_file in chapter_files[:5]:  # Sample first 5 chapters
                try:
                    xml_content = zf.read(chapter_file)
                    chapter_root = ET.fromstring(xml_content)
                    
                    # Count imagedata/graphic elements
                    media_refs = len(chapter_root.findall('.//imagedata')) + len(chapter_root.findall('.//graphic'))
                    table_refs = len(chapter_root.findall('.//table'))
                    
                    total_media_refs += media_refs
                    total_table_refs += table_refs
                    
                    if media_refs > 0 or table_refs > 0:
                        print(f"  {chapter_file}: {media_refs} images, {table_refs} tables")
                        
                except Exception as e:
                    print(f"  ⚠ Error reading {chapter_file}: {e}")
            
            print(f"\n📊 Sample totals (first 5 chapters):")
            print(f"  Images referenced: {total_media_refs}")
            print(f"  Tables referenced: {total_table_refs}")
            
            return {
                'total_files': len(file_list),
                'chapter_files': len(chapter_files),
                'multimedia_files': len(multimedia_files),
            }
            
    except zipfile.BadZipFile as e:
        print(f"❌ Invalid ZIP file: {e}")
        return None


def main():
    print("\n" + "="*70)
    print("DIAGNOSTIC: Empty <media /> and <tables /> Analysis")
    print("="*70)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python diagnose_empty_media_tables.py <base_name>")
        print("\nExample:")
        print("  python diagnose_empty_media_tables.py 9780803694958")
        print("\nThis will analyze:")
        print("  - 9780803694958_MultiMedia.xml")
        print("  - 9780803694958_unified.xml")
        print("  - 9780803694958.zip (or pre_fixes_9780803694958.zip)")
        return
    
    base_name = sys.argv[1]
    
    # Find files
    multimedia_xml = f"{base_name}_MultiMedia.xml"
    unified_xml = f"{base_name}_unified.xml"
    package_zip = f"{base_name}.zip"
    package_zip_prefixes = f"pre_fixes_{base_name}.zip"
    
    # Analyze MultiMedia.xml
    multimedia_data = analyze_multimedia_xml(multimedia_xml)
    
    # Analyze unified.xml
    unified_data = analyze_unified_xml(unified_xml)
    
    # Compare results
    if multimedia_data and unified_data:
        print(f"\n{'='*70}")
        print("COMPARISON & DIAGNOSIS")
        print(f"{'='*70}")
        
        media_diff = multimedia_data['total_media'] - unified_data['total_media']
        table_diff = multimedia_data['total_tables'] - unified_data['total_tables']
        
        print(f"\n📊 Media Transfer:")
        print(f"  MultiMedia.xml: {multimedia_data['total_media']} media elements")
        print(f"  Unified.xml: {unified_data['total_media']} media elements")
        if media_diff > 0:
            print(f"  ❌ MISSING: {media_diff} media elements not transferred!")
        elif media_diff < 0:
            print(f"  ⚠ WARNING: More media in unified.xml than MultiMedia.xml?")
        else:
            print(f"  ✅ All media transferred successfully")
        
        print(f"\n📊 Table Transfer:")
        print(f"  MultiMedia.xml: {multimedia_data['total_tables']} table elements")
        print(f"  Unified.xml: {unified_data['total_tables']} table elements")
        if table_diff > 0:
            print(f"  ❌ MISSING: {table_diff} table elements not transferred!")
        elif table_diff < 0:
            print(f"  ⚠ WARNING: More tables in unified.xml than MultiMedia.xml?")
        else:
            print(f"  ✅ All tables transferred successfully")
        
        # Check for empty wrappers
        if unified_data['pages_with_empty_media'] > 0:
            print(f"\n⚠ {unified_data['pages_with_empty_media']} pages have empty <media> wrappers")
            print(f"  This is EXPECTED - not all pages have media")
        
        if unified_data['pages_with_empty_tables'] > 0:
            print(f"\n⚠ {unified_data['pages_with_empty_tables']} pages have empty <tables> wrappers")
            print(f"  This is EXPECTED - not all pages have tables")
    
    # Check package if exists
    if Path(package_zip).exists():
        package_data = check_package_zip(package_zip)
    elif Path(package_zip_prefixes).exists():
        package_data = check_package_zip(package_zip_prefixes)
    
    print(f"\n{'='*70}")
    print("EXPLANATION & EXPECTED BEHAVIOR")
    print(f"{'='*70}")
    print("""
The <media /> and <tables /> tags in _unified.xml are NOT supposed to be 
populated with actual content!

Here's how the pipeline works:

1. MultiMedia_Image_Extractor.py:
   - Extracts all images and tables from PDF
   - Saves them to MultiMedia/ folder
   - Creates MultiMedia.xml with metadata

2. pdf_to_unified_xml.py:
   - Creates unified.xml with TEXT and PLACEHOLDERS for media/tables
   - Each page has:
     * <texts> with text fragments
     * <media> wrapper with <media> elements (EMPTY self-closing tags)
     * <tables> wrapper with <table> elements (EMPTY self-closing tags)
   - These are PLACEHOLDERS with reading_order and bbox info

3. heuristics_Nov3.py (DocBook conversion):
   - Reads unified.xml 
   - Transforms into DocBook structure
   - Converts <media> placeholders into <figure><mediaobject><imagedata>
   - Converts <table> placeholders into DocBook <table> elements

4. package.py:
   - Takes DocBook XML
   - Copies media files from MultiMedia/ folder into ZIP
   - Updates fileref attributes to point to MultiMedia/filename.jpg

SO: Empty <media /> and <tables /> tags in _unified.xml are CORRECT!
They are just placeholders for positioning. The actual content is added
during DocBook conversion and packaging.

If images are missing from chapter XMLs, the issue is likely in:
- heuristics_Nov3.py (not converting placeholders)
- package.py (not finding/copying media files)
""")


if __name__ == "__main__":
    main()
