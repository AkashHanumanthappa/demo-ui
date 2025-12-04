#!/usr/bin/env python3
"""
Alternative Strategy: Keep Vectors, Remove Overlapping Rasters

This script demonstrates how to implement the opposite approach:
- Keep vector drawings that contain raster images
- Remove the redundant raster images
- Use this for flowcharts, annotated diagrams, etc.

Usage:
    python3 alternative_strategy_example.py input.pdf
"""

import os
import sys
import xml.etree.ElementTree as ET
from typing import List, Tuple


def calculate_overlap_ratio(raster_bbox: Tuple[float, float, float, float],
                            vector_bbox: Tuple[float, float, float, float]) -> float:
    """
    Calculate what percentage of the raster is contained in the vector region.
    
    Returns:
        Float between 0.0 and 1.0 representing overlap ratio
    """
    r_x1, r_y1, r_x2, r_y2 = raster_bbox
    v_x1, v_y1, v_x2, v_y2 = vector_bbox
    
    # Calculate intersection
    x_overlap = max(0, min(v_x2, r_x2) - max(v_x1, r_x1))
    y_overlap = max(0, min(v_y2, r_y2) - max(v_y1, r_y1))
    intersection_area = x_overlap * y_overlap
    
    # Calculate raster area
    raster_area = (r_x2 - r_x1) * (r_y2 - r_y1)
    
    if raster_area == 0:
        return 0.0
    
    return intersection_area / raster_area


def remove_redundant_rasters(xml_path: str, media_dir: str, overlap_threshold: float = 0.2):
    """
    Remove raster images that are contained within vector regions.
    
    This implements the alternative strategy where vectors are kept
    and overlapping rasters are removed.
    
    Args:
        xml_path: Path to MultiMedia.xml file
        media_dir: Path to MultiMedia directory with image files
        overlap_threshold: Minimum overlap ratio to consider raster redundant (default: 0.2)
    """
    print(f"\nProcessing: {xml_path}")
    print(f"Strategy: Keep vectors, remove overlapping rasters")
    print(f"Overlap threshold: {overlap_threshold * 100}%\n")
    
    # Parse XML
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    total_rasters_removed = 0
    total_files_deleted = 0
    
    # Process each page
    for page_elem in root.findall("page"):
        page_num = page_elem.get("index", "?")
        
        # Get all media elements on this page
        media_elements = page_elem.findall("media")
        
        # Separate rasters and vectors
        rasters = []
        vectors = []
        
        for media in media_elements:
            media_type = media.get("type")
            bbox = (
                float(media.get("x1", "0")),
                float(media.get("y1", "0")),
                float(media.get("x2", "0")),
                float(media.get("y2", "0"))
            )
            
            if media_type == "raster":
                rasters.append((media, bbox))
            elif media_type == "vector":
                vectors.append((media, bbox))
        
        if not rasters or not vectors:
            continue  # Nothing to process on this page
        
        print(f"Page {page_num}:")
        print(f"  Found {len(rasters)} raster(s) and {len(vectors)} vector(s)")
        
        # Check each raster against all vectors
        rasters_to_remove = []
        
        for raster_elem, raster_bbox in rasters:
            raster_id = raster_elem.get("id", "unknown")
            raster_file = raster_elem.get("file", "")
            
            for vector_elem, vector_bbox in vectors:
                vector_id = vector_elem.get("id", "unknown")
                
                # Calculate overlap
                overlap_ratio = calculate_overlap_ratio(raster_bbox, vector_bbox)
                
                if overlap_ratio > overlap_threshold:
                    print(f"    {raster_id}: {overlap_ratio*100:.1f}% inside {vector_id} → REMOVE")
                    
                    rasters_to_remove.append(raster_elem)
                    
                    # Delete the image file
                    if raster_file:
                        img_path = os.path.join(media_dir, raster_file)
                        if os.path.exists(img_path):
                            os.remove(img_path)
                            total_files_deleted += 1
                            print(f"      Deleted: {raster_file}")
                    
                    # Mark vector as composite
                    vector_elem.set("composite", "true")
                    vector_elem.set("contains_raster", raster_id)
                    
                    break  # Don't check other vectors for this raster
        
        # Remove raster elements from XML
        for raster_elem in rasters_to_remove:
            page_elem.remove(raster_elem)
            total_rasters_removed += 1
    
    # Save modified XML
    backup_path = xml_path.replace(".xml", "_backup.xml")
    print(f"\nSaving backup: {backup_path}")
    tree.write(backup_path, encoding="utf-8", xml_declaration=True)
    
    print(f"Saving modified XML: {xml_path}")
    ET.indent(tree, space="  ")
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    
    print(f"\n" + "="*60)
    print(f"Summary:")
    print(f"  - Raster elements removed from XML: {total_rasters_removed}")
    print(f"  - Image files deleted: {total_files_deleted}")
    print(f"  - Backup saved: {backup_path}")
    print("="*60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Remove raster images that overlap with vector regions (alternative strategy)"
    )
    parser.add_argument("pdf_path", help="Path to input PDF (will use PDF_MultiMedia.xml)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.2,
        help="Overlap threshold (0.0-1.0, default: 0.2 = 20%%)"
    )
    
    args = parser.parse_args()
    
    # Construct paths
    base_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
    base_dir = os.path.dirname(os.path.abspath(args.pdf_path))
    
    xml_path = os.path.join(base_dir, f"{base_name}_MultiMedia.xml")
    media_dir = os.path.join(base_dir, f"{base_name}_MultiMedia")
    
    if not os.path.exists(xml_path):
        print(f"Error: {xml_path} not found!")
        print(f"Please run: python3 pdf_to_unified_xml.py {args.pdf_path}")
        sys.exit(1)
    
    if not os.path.exists(media_dir):
        print(f"Error: {media_dir} not found!")
        sys.exit(1)
    
    # Process
    remove_redundant_rasters(xml_path, media_dir, args.threshold)
    
    print("\n✓ Done! Vectors are now prioritized over rasters.")
    print("\nTo revert, restore from backup:")
    print(f"  cp {xml_path.replace('.xml', '_backup.xml')} {xml_path}")


if __name__ == "__main__":
    main()
