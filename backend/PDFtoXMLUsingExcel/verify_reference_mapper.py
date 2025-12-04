#!/usr/bin/env python3
"""
Quick verification script to check if reference mapper fix is working.

Run this after processing a PDF to verify the mapper was populated.
"""

import sys
import json
from pathlib import Path

def check_mapping_file(mapping_path):
    """Check a reference mapping JSON file."""
    print(f"\n{'='*70}")
    print(f"Checking: {mapping_path}")
    print(f"{'='*70}")
    
    if not Path(mapping_path).exists():
        print(f"❌ File not found!")
        return False
    
    try:
        with open(mapping_path, 'r') as f:
            data = json.load(f)
        
        # Check metadata
        metadata = data.get('metadata', {})
        total_resources = metadata.get('total_resources', 0)
        
        # Check statistics
        stats = data.get('statistics', {})
        total_images = stats.get('total_images', 0)
        raster_images = stats.get('raster_images', 0)
        vector_images = stats.get('vector_images', 0)
        
        print(f"\n📊 Summary:")
        print(f"  Total resources: {total_resources}")
        print(f"  Total images: {total_images}")
        print(f"    - Raster: {raster_images}")
        print(f"    - Vector: {vector_images}")
        
        if total_resources == 0:
            print(f"\n❌ PROBLEM: Mapper is empty (0 resources)")
            print(f"  This means images were not registered during extraction.")
            print(f"  The fix may not have been applied correctly.")
            return False
        
        # Check resources
        resources = data.get('resources', {})
        if resources:
            print(f"\n✅ Mapper has {len(resources)} resources!")
            
            # Show sample
            print(f"\n📄 Sample (first 3 resources):")
            for i, (key, resource) in enumerate(list(resources.items())[:3]):
                print(f"\n  {i+1}. {key}")
                print(f"     Original: {resource.get('original_path')}")
                print(f"     Intermediate: {resource.get('intermediate_name')}")
                print(f"     Final: {resource.get('final_name', 'NOT SET')}")
                print(f"     Type: {resource.get('resource_type')}")
                
                # Check if it's a Phase 1 or final mapping
                if resource.get('final_name'):
                    print(f"     Chapter: {resource.get('chapter_id', 'N/A')}")
                    print(f"     ✓ Final name assigned (packaging complete)")
                else:
                    print(f"     ⏳ Final name not yet assigned (pre-packaging)")
            
            return True
        else:
            print(f"\n❌ PROBLEM: Resources dict is empty")
            return False
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False


def check_import():
    """Check if reference_mapper module imports."""
    print(f"\n{'='*70}")
    print(f"Checking reference_mapper module import...")
    print(f"{'='*70}")
    
    try:
        from reference_mapper import get_mapper, reset_mapper
        print(f"✅ Module imports successfully")
        
        # Test basic functionality
        mapper = get_mapper()
        print(f"✅ get_mapper() works")
        print(f"   Current resources: {len(mapper.resources)}")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print(f"   Make sure reference_mapper.py is in the same directory")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print(f"\n{'='*70}")
    print(f"Reference Mapper Verification Tool")
    print(f"{'='*70}")
    
    # Check import first
    import_ok = check_import()
    
    if not import_ok:
        print(f"\n{'='*70}")
        print(f"RESULT: Cannot proceed - reference_mapper not available")
        print(f"{'='*70}")
        return
    
    # Check for mapping files
    if len(sys.argv) < 2:
        print(f"\n📝 Usage:")
        print(f"  python verify_reference_mapper.py <base_name>")
        print(f"\nExample:")
        print(f"  python verify_reference_mapper.py 9780803694958")
        print(f"\nOr specify full path:")
        print(f"  python verify_reference_mapper.py path/to/mapping.json")
        print(f"\nThis will check:")
        print(f"  - {sys.argv[0].replace('verify_reference_mapper.py', '')}<base>_reference_mapping_phase1.json")
        print(f"  - {sys.argv[0].replace('verify_reference_mapper.py', '')}<base>_reference_mapping.json")
        return
    
    base_name = sys.argv[1]
    
    # If full path provided, use it
    if base_name.endswith('.json'):
        mapping_files = [Path(base_name)]
    else:
        # Try standard naming patterns
        mapping_files = [
            Path(f"{base_name}_reference_mapping_phase1.json"),
            Path(f"{base_name}_reference_mapping.json"),
        ]
    
    results = []
    for mapping_file in mapping_files:
        result = check_mapping_file(str(mapping_file))
        results.append((mapping_file, result))
    
    # Summary
    print(f"\n{'='*70}")
    print(f"VERIFICATION SUMMARY")
    print(f"{'='*70}")
    
    found_good = False
    for mapping_file, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        exists = "✓" if mapping_file.exists() else "✗"
        print(f"  [{exists}] {mapping_file.name}: {status}")
        if result:
            found_good = True
    
    if found_good:
        print(f"\n✅ At least one valid mapping found - fix is working!")
    else:
        print(f"\n❌ No valid mappings found - fix may need attention")
        print(f"\nTroubleshooting:")
        print(f"  1. Make sure you ran the pipeline with the fix applied")
        print(f"  2. Check console output for 'Reference mapper initialized'")
        print(f"  3. Check console output for 'Reference mapping exported'")
        print(f"  4. Verify Multipage_Image_Extractor.py can import reference_mapper")


if __name__ == "__main__":
    main()
