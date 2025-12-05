#!/usr/bin/env python3
"""
Analyze Remaining DTD Validation Errors

This script analyzes the remaining validation errors from a RittDoc validation
and provides a detailed breakdown of error patterns to help create targeted fixes.
"""

import re
import sys
import zipfile
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
from lxml import etree


class ErrorAnalyzer:
    """Analyzes DTD validation errors to identify patterns and suggest fixes"""

    def __init__(self, dtd_path: Path):
        self.dtd_path = dtd_path
        self.dtd = etree.DTD(str(dtd_path))
        self.errors_by_type = defaultdict(list)
        self.errors_by_element = defaultdict(list)
        self.errors_by_file = defaultdict(list)

    def analyze_zip_package(self, zip_path: Path) -> Dict:
        """
        Analyze all chapter files in a ZIP package and categorize errors.
        
        Returns:
            Dictionary with error analysis results
        """
        print(f"\n{'='*80}")
        print("ANALYZING REMAINING VALIDATION ERRORS")
        print(f"{'='*80}\n")
        
        print(f"Package: {zip_path}")
        print(f"DTD: {self.dtd_path}\n")

        # Extract ZIP to temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmpdir_path)
            
            # Find Book.XML to get chapter list
            book_xml = tmpdir_path / "Book.XML"
            if not book_xml.exists():
                print(f"✗ Book.XML not found in package")
                return {}
            
            # Extract entity declarations
            entities = self._extract_entities(book_xml)
            print(f"Found {len(entities)} chapter entity references\n")
            
            # Validate each chapter
            total_errors = 0
            files_with_errors = 0
            
            for entity_name, filename in sorted(entities.items()):
                chapter_path = tmpdir_path / filename
                if not chapter_path.exists():
                    print(f"  ⚠ {filename}: File not found")
                    continue
                
                errors = self._validate_chapter(chapter_path, filename)
                
                if errors:
                    files_with_errors += 1
                    total_errors += len(errors)
                    self.errors_by_file[filename] = errors
                    print(f"  {filename}: {len(errors)} error(s)")
                else:
                    print(f"  {filename}: ✓ Valid")
        
        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Files with errors: {files_with_errors}")
        print(f"Total errors: {total_errors}\n")
        
        # Analyze error patterns
        analysis = self._analyze_patterns()
        self._print_analysis(analysis)
        
        return analysis

    def _extract_entities(self, book_xml_path: Path) -> Dict[str, str]:
        """Extract entity declarations from Book.XML"""
        entities = {}
        with open(book_xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doctype_match = re.search(r'<!DOCTYPE[^>]+\[(.*?)\]>', content, re.DOTALL)
        if doctype_match:
            doctype_content = doctype_match.group(1)
            entity_pattern = r'<!ENTITY\s+(\w+)\s+SYSTEM\s+"([^"]+)">'
            for match in re.finditer(entity_pattern, doctype_content):
                entities[match.group(1)] = match.group(2)
        
        return entities

    def _validate_chapter(self, chapter_path: Path, filename: str) -> List[Dict]:
        """Validate a single chapter and return structured errors"""
        errors = []
        
        try:
            parser = etree.XMLParser(load_dtd=False, dtd_validation=False)
            tree = etree.parse(str(chapter_path), parser)
            root = tree.getroot()
            
            # Validate against DTD
            is_valid = self.dtd.validate(root)
            
            if not is_valid:
                for error in self.dtd.error_log:
                    error_info = {
                        'file': filename,
                        'line': error.line,
                        'column': error.column,
                        'message': error.message,
                        'type': error.type_name,
                        'level': error.level_name
                    }
                    errors.append(error_info)
                    
                    # Categorize by element
                    element_match = re.search(r'Element (\w+)', error.message)
                    if element_match:
                        element_name = element_match.group(1)
                        self.errors_by_element[element_name].append(error_info)
                    
                    # Categorize by error type
                    self.errors_by_type[error.type_name].append(error_info)
        
        except Exception as e:
            print(f"    Error parsing {filename}: {e}")
        
        return errors

    def _analyze_patterns(self) -> Dict:
        """Analyze error patterns and identify common issues"""
        analysis = {
            'error_types': dict(Counter([e['type'] for errors in self.errors_by_file.values() for e in errors])),
            'top_elements': dict(Counter([k for k, v in self.errors_by_element.items() if len(v) > 5]).most_common(10)),
            'error_messages': Counter([e['message'] for errors in self.errors_by_file.values() for e in errors]).most_common(10),
            'files_most_errors': sorted([(k, len(v)) for k, v in self.errors_by_file.items()], key=lambda x: x[1], reverse=True)[:10]
        }
        return analysis

    def _print_analysis(self, analysis: Dict):
        """Print detailed error analysis"""
        print(f"{'='*80}")
        print("ERROR ANALYSIS")
        print(f"{'='*80}\n")
        
        # Error types breakdown
        print("1. ERROR TYPES:")
        print("-" * 80)
        for error_type, count in sorted(analysis['error_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {error_type}: {count}")
        
        # Top problematic elements
        print(f"\n2. TOP PROBLEMATIC ELEMENTS (>5 errors):")
        print("-" * 80)
        for element, count in sorted(analysis['top_elements'].items(), key=lambda x: x[1], reverse=True):
            print(f"  <{element}>: {count} errors")
        
        # Most common error messages
        print(f"\n3. MOST COMMON ERROR MESSAGES:")
        print("-" * 80)
        for i, (message, count) in enumerate(analysis['error_messages'], 1):
            # Truncate long messages
            short_msg = message[:100] + "..." if len(message) > 100 else message
            print(f"  {i}. [{count}x] {short_msg}")
        
        # Files with most errors
        print(f"\n4. FILES WITH MOST ERRORS:")
        print("-" * 80)
        for filename, error_count in analysis['files_most_errors']:
            print(f"  {filename}: {error_count} errors")
        
        print(f"\n{'='*80}")
        print("DETAILED ERROR PATTERNS")
        print(f"{'='*80}\n")
        
        # Analyze specific error patterns
        self._analyze_figure_errors()
        self._analyze_content_model_errors()

    def _analyze_figure_errors(self):
        """Analyze figure-specific errors in detail"""
        figure_errors = self.errors_by_element.get('figure', [])
        
        if not figure_errors:
            print("No figure-related errors found.\n")
            return
        
        print(f"FIGURE ELEMENT ERRORS ({len(figure_errors)} total):")
        print("-" * 80)
        
        # Group by unique message
        message_groups = defaultdict(list)
        for error in figure_errors:
            message_groups[error['message']].append(error)
        
        for message, errors in sorted(message_groups.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n  Message: {message}")
            print(f"  Occurrences: {len(errors)}")
            print(f"  Sample files: {', '.join(set([e['file'] for e in errors[:5]]))}")
            
            # Try to extract what the DTD expects
            if "expecting" in message:
                expected_match = re.search(r'expecting \((.*?)\)', message)
                if expected_match:
                    expected = expected_match.group(1)
                    print(f"  DTD expects: {expected}")
        
        print()

    def _analyze_content_model_errors(self):
        """Analyze content model errors in detail"""
        content_errors = [e for errors in self.errors_by_file.values() 
                         for e in errors if 'content does not match' in e['message'].lower()]
        
        if not content_errors:
            print("No content model errors found.\n")
            return
        
        print(f"CONTENT MODEL ERRORS ({len(content_errors)} total):")
        print("-" * 80)
        
        # Extract elements involved
        element_violations = defaultdict(int)
        for error in content_errors:
            element_match = re.search(r'Element (\w+) content', error['message'])
            if element_match:
                element_violations[element_match.group(1)] += 1
        
        print("\nElements with content model violations:")
        for element, count in sorted(element_violations.items(), key=lambda x: x[1], reverse=True):
            print(f"  <{element}>: {count} violations")
        
        print()

    def generate_fix_suggestions(self, analysis: Dict) -> List[str]:
        """Generate specific fix suggestions based on error analysis"""
        suggestions = []
        
        print(f"{'='*80}")
        print("FIX SUGGESTIONS")
        print(f"{'='*80}\n")
        
        # Analyze figure errors
        figure_errors = self.errors_by_element.get('figure', [])
        if figure_errors:
            suggestions.append(
                "FIX 1: Figure Content Model Issues\n"
                "--------------------------------------\n"
                "Problem: Figure elements don't match DTD requirements\n"
                "Common causes:\n"
                "  - Missing required <title> element\n"
                "  - Missing required <mediaobject> or <graphic> child\n"
                "  - Empty or placeholder content\n"
                "  - Incorrect child element order\n"
                "\n"
                "Solution:\n"
                "  - Add missing <title> if not present\n"
                "  - Ensure figure has <mediaobject> or <graphic> child\n"
                "  - Remove empty figures or convert to <para>\n"
                "  - Check element order: <title>, then <mediaobject>"
            )
        
        # Analyze table errors
        table_errors = self.errors_by_element.get('table', [])
        if table_errors:
            suggestions.append(
                "FIX 2: Table Content Model Issues\n"
                "--------------------------------------\n"
                "Problem: Table elements missing required attributes or children\n"
                "Common causes:\n"
                "  - Missing 'cols' attribute in <tgroup>\n"
                "  - Missing <tbody> element\n"
                "  - Invalid table structure\n"
                "\n"
                "Solution:\n"
                "  - Add cols=\"N\" attribute to <tgroup> (count columns)\n"
                "  - Ensure <tbody> is present\n"
                "  - Verify structure: <table><title><tgroup><tbody>"
            )
        
        # Analyze sect errors
        sect_errors = [e for k, v in self.errors_by_element.items() if k.startswith('sect') for e in v]
        if sect_errors:
            suggestions.append(
                "FIX 3: Section Content Model Issues\n"
                "--------------------------------------\n"
                "Problem: Section elements have invalid content\n"
                "Common causes:\n"
                "  - Missing required <title> element\n"
                "  - Invalid child elements\n"
                "  - Empty sections\n"
                "\n"
                "Solution:\n"
                "  - Add <title> as first child of section\n"
                "  - Wrap content in <para> if needed\n"
                "  - Remove or merge empty sections"
            )
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{suggestion}\n")
        
        return suggestions


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_remaining_errors.py <package.zip> [dtd_path]")
        print("\nExample:")
        print("  python3 analyze_remaining_errors.py 9780989163286_rittdoc.zip")
        sys.exit(1)
    
    zip_path = Path(sys.argv[1])
    if not zip_path.exists():
        print(f"✗ Error: ZIP file not found: {zip_path}")
        sys.exit(1)
    
    # Use provided DTD or default
    if len(sys.argv) > 2:
        dtd_path = Path(sys.argv[2])
    else:
        dtd_path = Path("RITTDOCdtd/v1.1/RittDocBook.dtd")
    
    if not dtd_path.exists():
        print(f"✗ Error: DTD file not found: {dtd_path}")
        sys.exit(1)
    
    # Run analysis
    analyzer = ErrorAnalyzer(dtd_path)
    analysis = analyzer.analyze_zip_package(zip_path)
    
    # Generate fix suggestions
    suggestions = analyzer.generate_fix_suggestions(analysis)
    
    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    print("1. Review the error patterns above")
    print("2. Use the targeted_dtd_fixer.py script (coming next)")
    print("3. Apply fixes iteratively until all errors are resolved")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
