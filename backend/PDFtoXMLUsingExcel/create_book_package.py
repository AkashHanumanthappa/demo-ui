#!/usr/bin/env python3
from pathlib import Path
from lxml import etree
import argparse

# import your packaging function
from package import (
    BOOK_DOCTYPE_SYSTEM_DEFAULT,
    package_docbook,
    make_file_fetcher,
)  # uses your existing implementation

def main():
    print("\n" + "="*70)
    print("BOOK PACKAGING SCRIPT")
    print("="*70)

    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to structured DocBook XML")
    p.add_argument("--out", required=True, help="Output directory for ZIP")
    p.add_argument(
        "--dtd",
        default=BOOK_DOCTYPE_SYSTEM_DEFAULT,
        help="System DTD to embed",
    )
    p.add_argument(
        "--metadata-dir",
        help="Directory containing metadata.csv or metadata.xls/xlsx (default: input directory)",
    )
    args = p.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out)

    print(f"\nInput XML: {in_path}")
    print(f"Output dir: {out_dir}")
    print(f"DTD: {args.dtd}\n")

    out_dir.mkdir(parents=True, exist_ok=True)

    print("  → Parsing structured XML...")
    root = etree.parse(str(in_path)).getroot()
    # Choose a sane filename base from the root tag or the input name
    base = (in_path.stem or "book")

    # Determine the base name by removing _structured* suffix if present
    # Handle variations like _structured, _structured_test, _structured_test2, etc.
    base_name = base
    if "_structured" in base:
        # Remove everything from _structured onwards
        base_name = base.split("_structured")[0]

    # Look for MultiMedia folder in the same directory as the input XML
    multimedia_folder = in_path.parent / f"{base_name}_MultiMedia"

    # If not found with base_name, try looking for any *_MultiMedia folder
    if not multimedia_folder.exists():
        # Look for any folder ending with _MultiMedia in the same directory
        multimedia_folders = list(in_path.parent.glob("*_MultiMedia"))
        if multimedia_folders:
            print(f"  → MultiMedia folder not found at {multimedia_folder}")
            print(f"  → Found alternative MultiMedia folder: {multimedia_folders[0]}")
            multimedia_folder = multimedia_folders[0]

    # Create media fetcher with search paths
    search_paths = []
    if multimedia_folder.exists():
        print(f"  → Found MultiMedia folder: {multimedia_folder}")
        search_paths.append(multimedia_folder)
        # Also add SharedImages subfolder
        shared_images = multimedia_folder / "SharedImages"
        if shared_images.exists():
            print(f"  → Found SharedImages folder: {shared_images}")
            search_paths.append(shared_images)
    else:
        print(f"  ⚠ Warning: MultiMedia folder not found at {multimedia_folder}")
        print(f"     Images may not be included in the package!")

    # Add the input directory as a fallback search path
    search_paths.append(in_path.parent)

    # Create media fetcher
    media_fetcher = make_file_fetcher(search_paths) if search_paths else None

    zip_path = out_dir / f"{base}.zip"

    # Determine metadata directory
    metadata_dir = Path(args.metadata_dir) if args.metadata_dir else in_path.parent
    
    print("  → Starting packaging process...")
    final_zip = package_docbook(
        root=root,
        root_name=(root.tag.split('}', 1)[-1] if root.tag.startswith('{') else root.tag),
        dtd_system=args.dtd,
        zip_path=str(zip_path),
        processing_instructions=[("xml-stylesheet", 'type="text/xsl" href="book.xsl"')],  # optional
        assets=[],
        media_fetcher=media_fetcher,
        book_doctype_system=args.dtd,
        metadata_dir=metadata_dir,
    )
    
    print("\n" + "="*70)
    print("✓ PACKAGING COMPLETE!")
    print("="*70)
    print(f"ZIP file: {final_zip}")
    print("="*70)

if __name__ == "__main__":
    main()