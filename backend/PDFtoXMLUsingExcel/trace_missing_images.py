#!/usr/bin/env python3
"""
Trace Missing Images - Find where images are lost in the pipeline

This script compares image counts at each stage:
1. MultiMedia.xml (extraction)
2. unified.xml (merging)
3. structured.xml (DocBook conversion)
4. Final package ZIP (packaging)

It identifies exactly where the image loss occurs.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import zipfile


def analyze_multimedia_xml(path):
    """Analyze MultiMedia.xml to see what was extracted."""
    print(f"\n{'='*70}")
    print(f"STAGE 1: MultiMedia.xml (Extraction)")
    print(f"{'='*70}")
    
    if not Path(path).exists():
        print(f"❌ File not found: {path}")
        return None
    
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
        return None
    
    media_by_page = defaultdict(list)
    tables_by_page = defaultdict(list)
    media_without_file = []
    
    for page_elem in root.findall('.//page'):
        page_num = page_elem.get('index', 'unknown')
        
        for media_elem in page_elem.findall('media'):
            media_id = media_elem.get('id', 'no-id')
            file_attr = media_elem.get('file')
            
            media_by_page[page_num].append({
                'id': media_id,
                'file': file_attr,
                'type': media_elem.get('type', 'unknown')
            })
            
            if not file_attr:
                media_without_file.append((page_num, media_id))
        
        for table_elem in page_elem.findall('table'):
            table_id = table_elem.get('id', 'no-id')
            file_attr = table_elem.get('file')
            tables_by_page[page_num].append({
                'id': table_id,
                'file': file_attr
            })
    
    total_media = sum(len(m) for m in media_by_page.values())
    total_tables = sum(len(t) for t in tables_by_page.values())
    
    print(f"✓ Total media elements: {total_media}")
    print(f"✓ Total table elements: {total_tables}")
    print(f"✓ Pages with media: {len(media_by_page)}")
    print(f"✓ Pages with tables: {len(tables_by_page)}")
    
    if media_without_file:
        print(f"\n⚠ WARNING: {len(media_without_file)} media elements WITHOUT file attribute:")
        for page, media_id in media_without_file[:10]:
            print(f"    Page {page}: {media_id}")
        if len(media_without_file) > 10:
            print(f"    ... and {len(media_without_file) - 10} more")
    
    # Show sample
    sample_page = list(media_by_page.keys())[0] if media_by_page else None
    if sample_page:
        print(f"\n📄 Sample (Page {sample_page}):")
        for media in media_by_page[sample_page][:3]:
            print(f"    {media['id']}: file={media['file']}")
    
    return {
        'total_media': total_media,
        'total_tables': total_tables,
        'media_by_page': media_by_page,
        'tables_by_page': tables_by_page,
        'media_without_file': len(media_without_file)
    }


def analyze_unified_xml(path):
    """Analyze unified.xml to see what was merged."""
    print(f"\n{'='*70}")
    print(f"STAGE 2: unified.xml (Merging)")
    print(f"{'='*70}")
    
    if not Path(path).exists():
        print(f"❌ File not found: {path}")
        return None
    
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
        return None
    
    media_count = 0
    table_count = 0
    media_with_file = 0
    pages_with_media = 0
    pages_with_tables = 0
    
    for page_elem in root.findall('.//page'):
        # Find <media> wrapper
        media_wrapper = page_elem.find('media')
        if media_wrapper is not None:
            media_elements = media_wrapper.findall('media')
            if media_elements:
                pages_with_media += 1
                for media_elem in media_elements:
                    media_count += 1
                    if media_elem.get('file'):
                        media_with_file += 1
        
        # Find <tables> wrapper
        tables_wrapper = page_elem.find('tables')
        if tables_wrapper is not None:
            table_elements = tables_wrapper.findall('table')
            if table_elements:
                pages_with_tables += 1
                table_count += len(table_elements)
    
    print(f"✓ Total <media> elements: {media_count}")
    print(f"✓ Media with file attribute: {media_with_file}")
    print(f"✓ Total <table> elements: {table_count}")
    print(f"✓ Pages with media: {pages_with_media}")
    print(f"✓ Pages with tables: {pages_with_tables}")
    
    if media_count != media_with_file:
        print(f"\n⚠ WARNING: {media_count - media_with_file} media elements lack file attribute")
    
    return {
        'total_media': media_count,
        'media_with_file': media_with_file,
        'total_tables': table_count,
        'pages_with_media': pages_with_media,
        'pages_with_tables': pages_with_tables
    }


def analyze_structured_xml(path):
    """Analyze structured.xml to see DocBook conversion."""
    print(f"\n{'='*70}")
    print(f"STAGE 3: structured.xml (DocBook Conversion)")
    print(f"{'='*70}")
    
    if not Path(path).exists():
        print(f"❌ File not found: {path}")
        return None
    
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"❌ XML Parse Error: {e}")
        return None
    
    # Count imagedata and graphic elements
    imagedata_count = len(root.findall('.//imagedata'))
    graphic_count = len(root.findall('.//graphic'))
    table_count = len(root.findall('.//table'))
    
    # Count those with fileref
    imagedata_with_fileref = sum(1 for elem in root.findall('.//imagedata') if elem.get('fileref'))
    
    # Sample filerefs
    sample_refs = []
    for elem in root.findall('.//imagedata')[:5]:
        fileref = elem.get('fileref', 'NO-FILEREF')
        sample_refs.append(fileref)
    
    print(f"✓ <imagedata> elements: {imagedata_count}")
    print(f"✓ <graphic> elements: {graphic_count}")
    print(f"✓ <table> elements: {table_count}")
    print(f"✓ imagedata with fileref: {imagedata_with_fileref}")
    
    if sample_refs:
        print(f"\n📄 Sample fileref values:")
        for ref in sample_refs:
            print(f"    {ref}")
    
    return {
        'imagedata_count': imagedata_count,
        'graphic_count': graphic_count,
        'total_images': imagedata_count + graphic_count,
        'table_count': table_count,
        'imagedata_with_fileref': imagedata_with_fileref
    }


def analyze_package_zip(path):
    """Analyze final ZIP package."""
    print(f"\n{'='*70}")
    print(f"STAGE 4: Final Package ZIP (Packaging)")
    print(f"{'='*70}")
    
    if not Path(path).exists():
        print(f"❌ File not found: {path}")
        return None
    
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            file_list = zf.namelist()
            
            # Count files
            chapter_xmls = [f for f in file_list if f.endswith('.xml') and f != 'Book.XML']
            multimedia_images = [f for f in file_list if f.startswith('MultiMedia/') and f.endswith(('.jpg', '.png', '.jpeg'))]
            
            print(f"✓ Chapter XMLs: {len(chapter_xmls)}")
            print(f"✓ Images in MultiMedia/: {len(multimedia_images)}")
            
            # Count images in chapter XMLs
            total_imagedata = 0
            for chapter_file in chapter_xmls[:5]:  # Sample first 5
                try:
                    xml_content = zf.read(chapter_file)
                    chapter_root = ET.fromstring(xml_content)
                    imagedata_count = len(chapter_root.findall('.//imagedata'))
                    total_imagedata += imagedata_count
                except Exception as e:
                    print(f"  ⚠ Error reading {chapter_file}: {e}")
            
            print(f"\n📄 Sample (first 5 chapters):")
            print(f"  Total <imagedata> elements: {total_imagedata}")
            
            # Show sample image filenames
            print(f"\n📁 Sample MultiMedia files:")
            for img in multimedia_images[:10]:
                print(f"    {img}")
            if len(multimedia_images) > 10:
                print(f"    ... and {len(multimedia_images) - 10} more")
            
            return {
                'chapter_count': len(chapter_xmls),
                'image_file_count': len(multimedia_images),
                'sample_imagedata_count': total_imagedata
            }
    except zipfile.BadZipFile as e:
        print(f"❌ Invalid ZIP file: {e}")
        return None


def main():
    print(f"\n{'='*70}")
    print(f"TRACE MISSING IMAGES - Pipeline Analysis")
    print(f"{'='*70}")
    
    if len(sys.argv) < 2:
        print(f"\nUsage:")
        print(f"  python trace_missing_images.py <base_name>")
        print(f"\nExample:")
        print(f"  python trace_missing_images.py 9780803694958")
        print(f"\nThis will analyze:")
        print(f"  1. 9780803694958_MultiMedia.xml")
        print(f"  2. 9780803694958_unified.xml")
        print(f"  3. 9780803694958_structured.xml")
        print(f"  4. 9780803694958.zip (or pre_fixes_9780803694958.zip)")
        return
    
    base_name = sys.argv[1]
    
    # File paths
    multimedia_xml = f"{base_name}_MultiMedia.xml"
    unified_xml = f"{base_name}_unified.xml"
    structured_xml = f"{base_name}_structured.xml"
    package_zip = f"{base_name}.zip"
    package_zip_prefixes = f"pre_fixes_{base_name}.zip"
    
    # Analyze each stage
    stage1 = analyze_multimedia_xml(multimedia_xml)
    stage2 = analyze_unified_xml(unified_xml)
    stage3 = analyze_structured_xml(structured_xml)
    
    # Try both ZIP names
    if Path(package_zip).exists():
        stage4 = analyze_package_zip(package_zip)
    elif Path(package_zip_prefixes).exists():
        stage4 = analyze_package_zip(package_zip_prefixes)
    else:
        stage4 = None
    
    # Summary
    print(f"\n{'='*70}")
    print(f"PIPELINE SUMMARY - Image Flow")
    print(f"{'='*70}")
    
    if stage1:
        print(f"\n📊 Stage 1 (Extraction):")
        print(f"  MultiMedia.xml: {stage1['total_media']} media elements")
        if stage1['media_without_file'] > 0:
            print(f"  ⚠ {stage1['media_without_file']} missing file attribute")
    
    if stage2:
        print(f"\n📊 Stage 2 (Merging):")
        print(f"  unified.xml: {stage2['total_media']} media elements")
        print(f"  With file attr: {stage2['media_with_file']}")
        
        if stage1 and stage2:
            diff = stage1['total_media'] - stage2['total_media']
            if diff != 0:
                print(f"  {'❌ LOST' if diff > 0 else '⚠ GAINED'}: {abs(diff)} media elements")
            else:
                print(f"  ✅ No loss in merging")
    
    if stage3:
        print(f"\n📊 Stage 3 (DocBook Conversion):")
        print(f"  structured.xml: {stage3['total_images']} image elements")
        print(f"    (<imagedata>: {stage3['imagedata_count']}, <graphic>: {stage3['graphic_count']})")
        
        if stage2 and stage3:
            diff = stage2['total_media'] - stage3['total_images']
            if diff != 0:
                print(f"  {'❌ LOST' if diff > 0 else '⚠ GAINED'}: {abs(diff)} images")
                if diff > 0:
                    print(f"  This is where images were filtered/lost!")
            else:
                print(f"  ✅ No loss in conversion")
    
    if stage4:
        print(f"\n📊 Stage 4 (Packaging):")
        print(f"  Package ZIP: {stage4['image_file_count']} image files")
        
        if stage3 and stage4:
            diff = stage3['total_images'] - stage4['image_file_count']
            if diff != 0:
                print(f"  {'❌ LOST' if diff > 0 else '⚠ GAINED'}: {abs(diff)} images")
                if diff > 0:
                    print(f"  Images lost during packaging - check media fetcher!")
            else:
                print(f"  ✅ No loss in packaging")
    
    # Diagnosis
    print(f"\n{'='*70}")
    print(f"DIAGNOSIS")
    print(f"{'='*70}")
    
    if stage1 and stage1['media_without_file'] > 0:
        print(f"\n🔍 Issue: {stage1['media_without_file']} media elements missing file attribute in MultiMedia.xml")
        print(f"   This means Multipage_Image_Extractor didn't set the filename.")
        print(f"   Action: Check extraction logs for errors.")
    
    if stage1 and stage2:
        if stage1['total_media'] != stage2['total_media']:
            print(f"\n🔍 Issue: Media count changed between extraction and merging")
            print(f"   MultiMedia.xml: {stage1['total_media']}")
            print(f"   unified.xml: {stage2['total_media']}")
            print(f"   Action: Check pdf_to_unified_xml.py merge logic.")
    
    if stage2 and stage3:
        if stage2['total_media'] > stage3['total_images']:
            print(f"\n🔍 Issue: {stage2['total_media'] - stage3['total_images']} images lost in DocBook conversion")
            print(f"   unified.xml: {stage2['total_media']} media")
            print(f"   structured.xml: {stage3['total_images']} images")
            print(f"   Action: Check heuristics_Nov3.py - are media elements being processed?")
    
    if stage3 and stage4:
        if stage3['total_images'] > stage4['image_file_count']:
            print(f"\n🔍 Issue: {stage3['total_images'] - stage4['image_file_count']} images lost in packaging")
            print(f"   structured.xml: {stage3['total_images']} images")
            print(f"   Package ZIP: {stage4['image_file_count']} files")
            print(f"   Action: Check package.py media fetcher and filtering rules.")
    
    if stage1 and stage2 and stage3 and stage4:
        if (stage1['total_media'] == stage2['total_media'] == stage3['total_images'] == stage4['image_file_count']):
            print(f"\n✅ NO ISSUES DETECTED - All {stage1['total_media']} images flow through correctly!")


if __name__ == "__main__":
    main()