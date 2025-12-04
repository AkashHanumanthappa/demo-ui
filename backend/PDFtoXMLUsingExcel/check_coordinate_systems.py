#!/usr/bin/env python3
"""
Check Coordinate Systems Across Pipeline

This script verifies that coordinates are consistent across all stages:
1. MultiMedia.xml (PyMuPDF coordinates)
2. unified.xml (should be HTML coordinates after transformation)
3. structured.xml (DocBook - coordinates may be removed)
4. Chapter XMLs in package (DocBook - coordinates typically not present)
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def analyze_multimedia_coords(path):
    """Check MultiMedia.xml coordinate system."""
    print(f"\n{'='*70}")
    print(f"STAGE 1: MultiMedia.xml (PyMuPDF Coordinates)")
    print(f"{'='*70}")
    
    if not Path(path).exists():
        print(f"❌ File not found: {path}")
        return None
    
    tree = ET.parse(path)
    root = tree.getroot()
    
    # Sample a few pages
    samples = []
    for page_elem in list(root.findall('.//page'))[:3]:
        page_num = page_elem.get('index')
        page_width = float(page_elem.get('width', 0))
        page_height = float(page_elem.get('height', 0))
        
        media_elem = page_elem.find('media')
        if media_elem is not None:
            x1 = float(media_elem.get('x1', 0))
            y1 = float(media_elem.get('y1', 0))
            x2 = float(media_elem.get('x2', 0))
            y2 = float(media_elem.get('y2', 0))
            
            samples.append({
                'page': page_num,
                'page_size': (page_width, page_height),
                'media_coords': (x1, y1, x2, y2),
                'media_id': media_elem.get('id', 'unknown')
            })
    
    if samples:
        print(f"\n📄 Sample pages:")
        for sample in samples:
            print(f"\n  Page {sample['page']}:")
            print(f"    Page size: {sample['page_size'][0]:.1f} x {sample['page_size'][1]:.1f} (PyMuPDF points)")
            print(f"    Media {sample['media_id']}:")
            print(f"      x1={sample['media_coords'][0]:.2f}, y1={sample['media_coords'][1]:.2f}")
            print(f"      x2={sample['media_coords'][2]:.2f}, y2={sample['media_coords'][3]:.2f}")
            
            # Check if coords are within page bounds
            if (sample['media_coords'][0] < 0 or sample['media_coords'][1] < 0 or
                sample['media_coords'][2] > sample['page_size'][0] or 
                sample['media_coords'][3] > sample['page_size'][1]):
                print(f"      ⚠ WARNING: Coordinates outside page bounds!")
    
    return samples


def analyze_unified_coords(path):
    """Check unified.xml coordinate system."""
    print(f"\n{'='*70}")
    print(f"STAGE 2: unified.xml (Should be HTML Coordinates)")
    print(f"{'='*70}")
    
    if not Path(path).exists():
        print(f"❌ File not found: {path}")
        return None
    
    tree = ET.parse(path)
    root = tree.getroot()
    
    # Sample a few pages
    samples = []
    for page_elem in list(root.findall('.//page'))[:3]:
        page_num = page_elem.get('number')
        page_width = float(page_elem.get('width', 0))
        page_height = float(page_elem.get('height', 0))
        
        # Check text coordinates
        text_elem = page_elem.find('.//texts/para/text')
        text_coords = None
        if text_elem is not None:
            text_coords = (
                float(text_elem.get('left', 0)),
                float(text_elem.get('top', 0)),
                float(text_elem.get('width', 0)),
                float(text_elem.get('height', 0))
            )
        
        # Check media coordinates
        media_wrapper = page_elem.find('media')
        media_coords = None
        media_id = None
        if media_wrapper is not None:
            media_elem = media_wrapper.find('media')
            if media_elem is not None:
                media_coords = (
                    float(media_elem.get('x1', 0)),
                    float(media_elem.get('y1', 0)),
                    float(media_elem.get('x2', 0)),
                    float(media_elem.get('y2', 0))
                )
                media_id = media_elem.get('id', 'unknown')
        
        samples.append({
            'page': page_num,
            'page_size': (page_width, page_height),
            'text_coords': text_coords,
            'media_coords': media_coords,
            'media_id': media_id
        })
    
    if samples:
        print(f"\n📄 Sample pages:")
        for sample in samples:
            print(f"\n  Page {sample['page']}:")
            print(f"    Page size: {sample['page_size'][0]:.1f} x {sample['page_size'][1]:.1f} (HTML/pdftohtml)")
            
            if sample['text_coords']:
                print(f"    Text sample:")
                print(f"      left={sample['text_coords'][0]:.1f}, top={sample['text_coords'][1]:.1f}")
                print(f"      width={sample['text_coords'][2]:.1f}, height={sample['text_coords'][3]:.1f}")
            
            if sample['media_coords']:
                print(f"    Media {sample['media_id']}:")
                print(f"      x1={sample['media_coords'][0]:.2f}, y1={sample['media_coords'][1]:.2f}")
                print(f"      x2={sample['media_coords'][2]:.2f}, y2={sample['media_coords'][3]:.2f}")
                
                # Check if coords are within page bounds
                if (sample['media_coords'][0] < 0 or sample['media_coords'][1] < 0 or
                    sample['media_coords'][2] > sample['page_size'][0] or 
                    sample['media_coords'][3] > sample['page_size'][1]):
                    print(f"      ⚠ WARNING: Coordinates outside page bounds!")
                
                # Check if media coords are in similar range as text coords
                if sample['text_coords']:
                    text_max = max(sample['text_coords'][0] + sample['text_coords'][2], 
                                  sample['text_coords'][1] + sample['text_coords'][3])
                    media_max = max(sample['media_coords'][2], sample['media_coords'][3])
                    
                    if abs(text_max - media_max) / max(text_max, media_max) > 0.5:
                        print(f"      ⚠ WARNING: Media coords seem to be in different scale than text!")
    
    return samples


def check_coordinate_transformation(multimedia_samples, unified_samples):
    """Verify coordinate transformation was applied correctly."""
    print(f"\n{'='*70}")
    print(f"COORDINATE TRANSFORMATION CHECK")
    print(f"{'='*70}")
    
    if not multimedia_samples or not unified_samples:
        print("⚠ Need both MultiMedia.xml and unified.xml to check transformation")
        return
    
    # Find matching pages
    for mm_sample in multimedia_samples:
        # Try to find matching page in unified (accounting for page number differences)
        for uni_sample in unified_samples:
            if mm_sample['media_id'] and uni_sample['media_id']:
                # Check if same media ID
                if mm_sample['media_id'] == uni_sample['media_id']:
                    print(f"\n📊 Checking transformation for {mm_sample['media_id']}:")
                    
                    mm_coords = mm_sample['media_coords']
                    uni_coords = uni_sample['media_coords']
                    mm_page = mm_sample['page_size']
                    uni_page = uni_sample['page_size']
                    
                    # Calculate expected scale factors
                    scale_x = uni_page[0] / mm_page[0]
                    scale_y = uni_page[1] / mm_page[1]
                    
                    print(f"  MultiMedia.xml page: {mm_page[0]:.1f} x {mm_page[1]:.1f}")
                    print(f"  unified.xml page: {uni_page[0]:.1f} x {uni_page[1]:.1f}")
                    print(f"  Expected scale factors: X={scale_x:.4f}, Y={scale_y:.4f}")
                    
                    # Check if coordinates were transformed
                    expected_x1 = mm_coords[0] * scale_x
                    expected_y1 = mm_coords[1] * scale_y
                    expected_x2 = mm_coords[2] * scale_x
                    expected_y2 = mm_coords[3] * scale_y
                    
                    print(f"\n  Original coords (PyMuPDF):")
                    print(f"    x1={mm_coords[0]:.2f}, y1={mm_coords[1]:.2f}")
                    print(f"    x2={mm_coords[2]:.2f}, y2={mm_coords[3]:.2f}")
                    
                    print(f"\n  Expected coords (after transformation):")
                    print(f"    x1={expected_x1:.2f}, y1={expected_y1:.2f}")
                    print(f"    x2={expected_x2:.2f}, y2={expected_y2:.2f}")
                    
                    print(f"\n  Actual coords in unified.xml:")
                    print(f"    x1={uni_coords[0]:.2f}, y1={uni_coords[1]:.2f}")
                    print(f"    x2={uni_coords[2]:.2f}, y2={uni_coords[3]:.2f}")
                    
                    # Check if transformation was applied
                    tolerance = 1.0  # 1 pixel tolerance
                    if (abs(uni_coords[0] - expected_x1) < tolerance and
                        abs(uni_coords[1] - expected_y1) < tolerance and
                        abs(uni_coords[2] - expected_x2) < tolerance and
                        abs(uni_coords[3] - expected_y2) < tolerance):
                        print(f"\n  ✅ Transformation applied correctly!")
                    else:
                        print(f"\n  ❌ Transformation NOT applied correctly!")
                        print(f"     Difference: x1={abs(uni_coords[0]-expected_x1):.2f}, y1={abs(uni_coords[1]-expected_y1):.2f}")
                    break


def analyze_structured_xml(path):
    """Check structured.xml (DocBook) - coordinates may be removed."""
    print(f"\n{'='*70}")
    print(f"STAGE 3: structured.xml (DocBook - Coordinates Usually Removed)")
    print(f"{'='*70}")
    
    if not Path(path).exists():
        print(f"❌ File not found: {path}")
        return
    
    tree = ET.parse(path)
    root = tree.getroot()
    
    # Check if any imagedata elements have coordinates
    imagedata_with_coords = []
    for elem in root.findall('.//imagedata')[:10]:
        coords = {}
        for attr in ['x', 'y', 'width', 'height', 'x1', 'y1', 'x2', 'y2']:
            if attr in elem.attrib:
                coords[attr] = elem.get(attr)
        
        if coords:
            imagedata_with_coords.append({
                'fileref': elem.get('fileref', 'no-fileref'),
                'coords': coords
            })
    
    print(f"\n📄 DocBook imagedata elements:")
    print(f"  Total imagedata: {len(root.findall('.//imagedata'))}")
    print(f"  With coordinate attributes: {len(imagedata_with_coords)}")
    
    if imagedata_with_coords:
        print(f"\n  ⚠ DocBook typically doesn't include coordinates!")
        print(f"  Sample elements with coordinates:")
        for item in imagedata_with_coords[:3]:
            print(f"    {item['fileref']}: {item['coords']}")
    else:
        print(f"\n  ✅ Coordinates removed (expected for DocBook)")


def main():
    print(f"\n{'='*70}")
    print(f"COORDINATE SYSTEM VERIFICATION")
    print(f"{'='*70}")
    
    if len(sys.argv) < 2:
        print(f"\nUsage:")
        print(f"  python check_coordinate_systems.py <base_name>")
        print(f"\nExample:")
        print(f"  python check_coordinate_systems.py 9780803694958")
        return
    
    base_name = sys.argv[1]
    
    # File paths
    multimedia_xml = f"{base_name}_MultiMedia.xml"
    unified_xml = f"{base_name}_unified.xml"
    structured_xml = f"{base_name}_structured.xml"
    
    # Analyze each stage
    mm_samples = analyze_multimedia_coords(multimedia_xml)
    uni_samples = analyze_unified_coords(unified_xml)
    
    # Check transformation
    if mm_samples and uni_samples:
        check_coordinate_transformation(mm_samples, uni_samples)
    
    # Check structured XML
    analyze_structured_xml(structured_xml)
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"""
The pipeline uses TWO coordinate systems:

1. PyMuPDF (MultiMedia.xml):
   - Uses PDF points (typically 549x774, 595x842, etc.)
   - Origin: top-left
   - Used by: Multipage_Image_Extractor.py

2. HTML/pdftohtml (unified.xml):
   - Uses scaled coordinates (typically 823x1161, etc.)
   - Origin: top-left
   - Used by: pdftohtml, pdf_to_unified_xml.py
   - Scale factor: typically ~1.5x

The transform_media_coords_to_html() function in pdf_to_unified_xml.py
should convert PyMuPDF coords → HTML coords when creating unified.xml.

DocBook (structured.xml, chapter XMLs):
   - Coordinates are REMOVED (DocBook doesn't use pixel coordinates)
   - Images referenced by fileref only
   - This is expected and correct for DocBook format

If media coordinates in unified.xml don't match text coordinates,
the transformation may not be working correctly!
    """)


if __name__ == "__main__":
    main()
