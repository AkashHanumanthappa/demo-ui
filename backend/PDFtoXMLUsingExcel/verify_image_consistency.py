#!/usr/bin/env python3
"""
Verification script to check consistency between MultiMedia folder and XML references.

This helps verify that the fix for the 177 missing images is working correctly.
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict


def count_multimedia_files(multimedia_dir):
    """Count image files in MultiMedia directory."""
    if not os.path.exists(multimedia_dir):
        print(f"ERROR: MultiMedia directory not found: {multimedia_dir}")
        return None
    
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    files = [f for f in os.listdir(multimedia_dir) 
             if os.path.isfile(os.path.join(multimedia_dir, f)) 
             and Path(f).suffix.lower() in image_extensions]
    
    return sorted(files)


def count_xml_references(xml_file):
    """Count <media> elements in XML output."""
    if not os.path.exists(xml_file):
        print(f"ERROR: XML file not found: {xml_file}")
        return None
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Count media elements by type
        media_by_type = defaultdict(list)
        for media in root.findall('.//media'):
            media_type = media.get('type', 'unknown')
            media_file = media.get('file', '')
            media_by_type[media_type].append(media_file)
        
        return media_by_type
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse XML: {e}")
        return None


def verify_consistency(multimedia_dir, xml_file):
    """Verify that file count matches XML reference count."""
    print("="*70)
    print("IMAGE CONSISTENCY VERIFICATION")
    print("="*70)
    print()
    
    # Count files in MultiMedia folder
    print(f"Checking MultiMedia folder: {multimedia_dir}")
    files = count_multimedia_files(multimedia_dir)
    if files is None:
        return False
    
    file_count = len(files)
    print(f"  ✓ Found {file_count} image files")
    
    # Count by page prefix
    page_counts = defaultdict(int)
    vector_count = 0
    raster_count = 0
    for f in files:
        if f.startswith('page'):
            # Extract page number
            parts = f.split('_')
            if len(parts) >= 2:
                page_num = parts[0].replace('page', '')
                page_counts[page_num] += 1
                if 'vector' in f:
                    vector_count += 1
                elif 'img' in f:
                    raster_count += 1
    
    print(f"    - Raster images: {raster_count}")
    print(f"    - Vector images: {vector_count}")
    print()
    
    # Count references in XML
    print(f"Checking XML file: {xml_file}")
    media_by_type = count_xml_references(xml_file)
    if media_by_type is None:
        return False
    
    total_xml_refs = sum(len(refs) for refs in media_by_type.values())
    print(f"  ✓ Found {total_xml_refs} <media> elements")
    
    for media_type, refs in media_by_type.items():
        print(f"    - {media_type}: {len(refs)} references")
    print()
    
    # Compare counts
    print("="*70)
    print("CONSISTENCY CHECK")
    print("="*70)
    
    if file_count == total_xml_refs:
        print(f"✓ PASS: File count ({file_count}) matches XML references ({total_xml_refs})")
        print()
        print("✓ No orphaned images detected!")
        print("✓ All images in MultiMedia folder are referenced in XML")
        print("✓ Fix is working correctly!")
        return True
    else:
        diff = abs(file_count - total_xml_refs)
        print(f"✗ FAIL: Mismatch detected!")
        print(f"  - Files in MultiMedia: {file_count}")
        print(f"  - References in XML: {total_xml_refs}")
        print(f"  - Difference: {diff} orphaned images")
        print()
        
        if file_count > total_xml_refs:
            print(f"⚠ {diff} image files have NO XML reference (orphaned)")
            print("  This means images were saved but not added to XML.")
            print("  The bug is still present!")
            
            # Find orphaned files
            xml_files = set()
            for refs in media_by_type.values():
                xml_files.update(refs)
            
            orphaned = [f for f in files if f not in xml_files]
            if orphaned:
                print()
                print(f"Orphaned files (first 10):")
                for f in orphaned[:10]:
                    print(f"  - {f}")
                if len(orphaned) > 10:
                    print(f"  ... and {len(orphaned) - 10} more")
        else:
            print(f"⚠ {diff} XML references have NO corresponding file")
            print("  This means XML references images that don't exist.")
            
            # Find missing files
            all_xml_files = set()
            for refs in media_by_type.values():
                all_xml_files.update(refs)
            
            file_set = set(files)
            missing = [f for f in all_xml_files if f not in file_set]
            if missing:
                print()
                print(f"Missing files (first 10):")
                for f in missing[:10]:
                    print(f"  - {f}")
                if len(missing) > 10:
                    print(f"  ... and {len(missing) - 10} more")
        
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 verify_image_consistency.py <multimedia_dir> <xml_file>")
        print()
        print("Example:")
        print("  python3 verify_image_consistency.py \\")
        print("    /path/to/output/book_MultiMedia \\")
        print("    /path/to/output/book_MultiMedia.xml")
        sys.exit(1)
    
    multimedia_dir = sys.argv[1]
    xml_file = sys.argv[2]
    
    success = verify_consistency(multimedia_dir, xml_file)
    
    print()
    print("="*70)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
