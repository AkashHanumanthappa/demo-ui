#!/usr/bin/env python3
"""
PDF Memory Diagnostic Tool

Analyzes a PDF file and estimates memory requirements for processing.
"""

import os
import sys
import argparse


def diagnose_pdf(pdf_path: str):
    """Analyze PDF and provide memory recommendations."""
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return 1
    
    print(f"\n{'='*70}")
    print("PDF MEMORY DIAGNOSTIC")
    print(f"{'='*70}\n")
    
    # Basic file info
    file_size_bytes = os.path.getsize(pdf_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    file_size_gb = file_size_mb / 1024
    
    print(f"📄 File: {os.path.basename(pdf_path)}")
    print(f"📏 Size: {file_size_mb:.1f} MB ({file_size_gb:.2f} GB)")
    
    # Try to get page count and detailed info
    try:
        import fitz  # PyMuPDF
        
        print("\n🔍 Opening PDF...")
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        
        # Get first page dimensions
        first_page = doc[0]
        page_width = first_page.rect.width
        page_height = first_page.rect.height
        
        # Sample a few pages for text/image density
        sample_pages = min(5, page_count)
        total_text_blocks = 0
        total_images = 0
        
        for i in range(sample_pages):
            page = doc[i]
            text_blocks = len(page.get_text("blocks"))
            images = len(page.get_images())
            total_text_blocks += text_blocks
            total_images += images
        
        avg_text_blocks = total_text_blocks / sample_pages
        avg_images = total_images / sample_pages
        
        doc.close()
        
        print(f"📑 Pages: {page_count}")
        print(f"📐 Page size: {page_width:.0f} x {page_height:.0f} points")
        print(f"📝 Avg text blocks per page: {avg_text_blocks:.0f}")
        print(f"🖼️  Avg images per page: {avg_images:.1f}")
        
        # Memory estimates
        print(f"\n{'='*70}")
        print("MEMORY ESTIMATES")
        print(f"{'='*70}\n")
        
        # Base PDF loading (PyMuPDF typically uses 3-5x file size)
        base_memory_mb = file_size_mb * 4
        
        # Image extraction memory (varies by DPI)
        # At 200 DPI: ~100MB per page
        # At 150 DPI: ~50MB per page
        # At 100 DPI: ~25MB per page
        image_memory_200dpi = page_count * 100
        image_memory_150dpi = page_count * 50
        image_memory_100dpi = page_count * 25
        
        # Table detection (Camelot) - about 50MB per page when active
        table_memory = page_count * 30
        
        # Total estimates
        total_200dpi = base_memory_mb + image_memory_200dpi + table_memory
        total_150dpi = base_memory_mb + image_memory_150dpi + table_memory
        total_100dpi = base_memory_mb + image_memory_100dpi + table_memory
        
        print("Estimated Peak Memory Usage:")
        print(f"  DPI 200 (default):  {total_200dpi:>7.0f} MB  ({total_200dpi/1024:>5.1f} GB)")
        print(f"  DPI 150 (medium):   {total_150dpi:>7.0f} MB  ({total_150dpi/1024:>5.1f} GB)")
        print(f"  DPI 100 (low):      {total_100dpi:>7.0f} MB  ({total_100dpi/1024:>5.1f} GB)")
        
        # Recommendations
        print(f"\n{'='*70}")
        print("RECOMMENDATIONS")
        print(f"{'='*70}\n")
        
        if total_200dpi > 16000:  # > 16GB
            print("⚠️  CRITICAL: This PDF is very large!")
            print("   Minimum RAM required: 32GB+")
            print("   Recommended DPI: 100")
            print("   Consider:")
            print("   - Processing on a high-memory server")
            print("   - Splitting PDF into smaller sections")
            rec_dpi = 100
            rec_memory = total_100dpi
        elif total_200dpi > 8000:  # > 8GB
            print("⚠️  WARNING: This PDF requires significant memory")
            print("   Minimum RAM required: 16GB")
            print("   Recommended DPI: 100-150")
            rec_dpi = 100
            rec_memory = total_100dpi
        elif total_200dpi > 4000:  # > 4GB
            print("⚠️  CAUTION: Monitor memory usage carefully")
            print("   Minimum RAM required: 8GB")
            print("   Recommended DPI: 150")
            rec_dpi = 150
            rec_memory = total_150dpi
        else:
            print("✅ This PDF should process without issues")
            print("   Minimum RAM required: 4GB")
            print("   Recommended DPI: 200 (default)")
            rec_dpi = 200
            rec_memory = total_200dpi
        
        # Generate commands
        print(f"\n{'='*70}")
        print("SUGGESTED COMMANDS")
        print(f"{'='*70}\n")
        
        pdf_basename = os.path.basename(pdf_path)
        
        print("Option 1: Use memory-efficient wrapper (RECOMMENDED)")
        print(f'  python3 pdf_processor_memory_efficient.py "{pdf_path}"')
        
        print("\nOption 2: Direct processing with recommended DPI")
        print(f'  python3 pdf_to_unified_xml.py "{pdf_path}" --dpi {rec_dpi} --full-pipeline')
        
        print("\nOption 3: Minimal processing (unified XML only, no DocBook)")
        print(f'  python3 pdf_to_unified_xml.py "{pdf_path}" --dpi {rec_dpi}')
        
        # System check
        print(f"\n{'='*70}")
        print("SYSTEM CHECK")
        print(f"{'='*70}\n")
        
        print("Check your available memory:")
        print("  Mac:   Run 'vm_stat' or check Activity Monitor")
        print("  Linux: Run 'free -h'")
        print(f"\nYou need at least {rec_memory/1024:.1f} GB of FREE RAM")
        print("(Total RAM should be higher to account for OS and other apps)")
        
    except ImportError:
        print("\n⚠️  PyMuPDF (fitz) not installed")
        print("Cannot analyze PDF details")
        print("\nInstall with: pip install PyMuPDF")
        
        # Rough estimate based on file size only
        print(f"\n{'='*70}")
        print("ROUGH ESTIMATES (based on file size only)")
        print(f"{'='*70}\n")
        
        if file_size_mb > 100:
            print("⚠️  Large file (> 100 MB)")
            print("   Estimated memory: 8-16 GB")
            print("   Recommended DPI: 100-150")
        elif file_size_mb > 50:
            print("Medium file (50-100 MB)")
            print("   Estimated memory: 4-8 GB")
            print("   Recommended DPI: 150")
        else:
            print("Small file (< 50 MB)")
            print("   Estimated memory: 2-4 GB")
            print("   Recommended DPI: 200 (default)")
    
    except Exception as e:
        print(f"\n⚠️  Error analyzing PDF: {e}")
        return 1
    
    print(f"\n{'='*70}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Analyze PDF and estimate memory requirements"
    )
    parser.add_argument("pdf_path", help="Path to PDF file")
    args = parser.parse_args()
    
    exit_code = diagnose_pdf(args.pdf_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
