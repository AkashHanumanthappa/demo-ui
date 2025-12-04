#!/usr/bin/env python3
"""
Test script to demonstrate improved list detection with indentation checking.
"""

import re
from dataclasses import dataclass, field
from typing import List, Sequence, Optional, Tuple

# Import the improved patterns and functions
# Note: This imports from heuristics_Nov3.py which requires lxml, so we'll mock the necessary parts

# Mock the Line class for testing
@dataclass
class Line:
    text: str
    left: float
    top: float
    height: float
    page_num: int = 1
    right: Optional[float] = None
    font_size: Optional[float] = 12.0

# Copy the improved regex pattern
ORDERED_LIST_RE = re.compile(r"^(?:\(?\d{1,3}[\.\)]|[A-HJ-Za-hj-z][\.\)])\s+(?=\w{2,})")

def _is_list_item(text: str, mapping: dict) -> tuple[bool, str, str]:
    """Improved list detection function."""
    stripped = text.lstrip()
    
    if len(stripped) < 3:
        return False, "", text
    
    pdf_cfg = mapping.get("pdf", {})
    markers = pdf_cfg.get("list_markers", [])
    
    # Check bullet markers
    for marker in markers:
        if marker == "-":
            if stripped.startswith("- "):
                remainder = stripped[2:].strip()
                if remainder and not remainder[0].isdigit():
                    return True, "itemized", remainder or text.strip()
        elif stripped.startswith(marker):
            remainder = stripped[len(marker):].strip()
            if remainder:
                return True, "itemized", remainder
    
    # Check ordered list patterns
    if ORDERED_LIST_RE.match(stripped):
        match = ORDERED_LIST_RE.match(stripped)
        if match:
            marker_text = match.group(0).strip()
            remainder = ORDERED_LIST_RE.sub("", stripped, count=1).strip()
            
            # Detect names like "A. Smith"
            if len(marker_text) == 2 and marker_text[0].isupper():
                words = remainder.split()
                if words and words[0] and words[0][0].isupper() and len(words[0]) > 2:
                    return False, "", text
            
            if remainder:
                return True, "ordered", remainder
    
    return False, "", text


def _line_gap(prev_line: Line, next_line: Line) -> float:
    """Calculate vertical gap between lines."""
    if prev_line.top is None or prev_line.height is None or next_line.top is None:
        return 0.0
    return next_line.top - (prev_line.top + prev_line.height)


def _detect_list_sequence(lines: Sequence[Line], start_idx: int, mapping: dict) -> Tuple[bool, str, int]:
    """Look ahead to confirm list with indentation checking."""
    if start_idx >= len(lines):
        return False, "", 0
    
    first_line = lines[start_idx]
    matched, list_type, _ = _is_list_item(first_line.text, mapping)
    
    if not matched:
        return False, "", 0
    
    # Check indentation
    first_indent = first_line.left if first_line.left is not None else 0
    consecutive_items = 1
    indent_tolerance = 15
    max_lookahead = 10
    
    for i in range(start_idx + 1, min(start_idx + max_lookahead, len(lines))):
        line = lines[i]
        
        if line.page_num != first_line.page_num:
            break
        
        # Check vertical gap
        prev_line = lines[i - 1]
        gap = _line_gap(prev_line, line)
        if prev_line.height and line.height:
            max_gap = max(prev_line.height, line.height) * 2.5
            if gap > max_gap:
                break
        
        # Check indentation
        line_indent = line.left if line.left is not None else 0
        if abs(line_indent - first_indent) > indent_tolerance:
            break
        
        # Check if also a list item
        is_item, item_type, _ = _is_list_item(line.text, mapping)
        if is_item and item_type == list_type:
            consecutive_items += 1
        else:
            break
    
    # Require confirmation
    min_items = 2
    if list_type == "itemized":
        first_text = first_line.text.lstrip()
        if any(first_text.startswith(m) for m in ["•", "◦", "▪", "✓", "●"]):
            min_items = 1
    
    is_confirmed = consecutive_items >= min_items
    return is_confirmed, list_type, consecutive_items


# Test cases
def run_tests():
    """Run test cases comparing old vs new behavior."""
    
    mapping = {
        "pdf": {
            "list_markers": ["•", "◦", "▪", "✓", "●", "○", "■", "□", "–", "—"],
        }
    }
    
    print("=" * 80)
    print("LIST DETECTION IMPROVEMENTS - TEST RESULTS")
    print("=" * 80)
    print()
    
    # Test 1: Name detection
    print("TEST 1: Name Detection (should NOT be detected as list)")
    print("-" * 80)
    text = "A. Smith conducted extensive research on the topic"
    matched, list_type, cleaned = _is_list_item(text, mapping)
    print(f"Text: {text}")
    print(f"Result: {'❌ DETECTED' if matched else '✅ NOT DETECTED'} as list")
    print()
    
    # Test 2: Isolated numbered item
    print("TEST 2: Isolated Numbered Item (should NOT be list without consecutive items)")
    print("-" * 80)
    lines = [
        Line("1. Only one item here", left=100, top=100, height=12),
        Line("This is regular text", left=100, top=115, height=12),
    ]
    is_list, list_type, num_items = _detect_list_sequence(lines, 0, mapping)
    print(f"Lines: {[l.text for l in lines]}")
    print(f"Result: {'❌ DETECTED' if is_list else '✅ NOT DETECTED'} as list")
    print()
    
    # Test 3: Consecutive items (should be detected)
    print("TEST 3: Consecutive Numbered Items (SHOULD be detected)")
    print("-" * 80)
    lines = [
        Line("1. First item", left=100, top=100, height=12),
        Line("2. Second item", left=100, top=115, height=12),
        Line("3. Third item", left=100, top=130, height=12),
    ]
    is_list, list_type, num_items = _detect_list_sequence(lines, 0, mapping)
    print(f"Lines: {[l.text for l in lines]}")
    print(f"Result: {'✅ DETECTED' if is_list else '❌ NOT DETECTED'} as list ({num_items} items)")
    print()
    
    # Test 4: Different indentation
    print("TEST 4: Different Indentation (should NOT be grouped)")
    print("-" * 80)
    lines = [
        Line("1. First item", left=100, top=100, height=12),
        Line("2. Second item", left=150, top=115, height=12),  # Different indent
    ]
    is_list, list_type, num_items = _detect_list_sequence(lines, 0, mapping)
    print(f"Lines: {[l.text for l in lines]}")
    print(f"Indents: {[l.left for l in lines]}")
    print(f"Result: {'❌ DETECTED' if is_list else '✅ NOT DETECTED'} as list")
    print()
    
    # Test 5: Hyphen with number
    print("TEST 5: Hyphen with Number (should NOT be list)")
    print("-" * 80)
    text = "- 50 participants were selected for the study"
    matched, list_type, cleaned = _is_list_item(text, mapping)
    print(f"Text: {text}")
    print(f"Result: {'❌ DETECTED' if matched else '✅ NOT DETECTED'} as list")
    print()
    
    # Test 6: Strong bullet (single item OK)
    print("TEST 6: Strong Bullet Marker (SHOULD be detected even if single)")
    print("-" * 80)
    lines = [
        Line("• This is a bullet point", left=100, top=100, height=12),
        Line("Regular text follows", left=100, top=115, height=12),
    ]
    is_list, list_type, num_items = _detect_list_sequence(lines, 0, mapping)
    print(f"Lines: {[l.text for l in lines]}")
    print(f"Result: {'✅ DETECTED' if is_list else '❌ NOT DETECTED'} as list")
    print()
    
    # Test 7: Section heading with Roman numeral
    print("TEST 7: Section Heading with Roman Numeral I (should NOT be list)")
    print("-" * 80)
    text = "I. Introduction to the methodology"
    matched, list_type, cleaned = _is_list_item(text, mapping)
    print(f"Text: {text}")
    print(f"Result: {'❌ DETECTED' if matched else '✅ NOT DETECTED'} as list")
    print()
    
    # Test 8: Bullet list with proper indentation
    print("TEST 8: Bullet List with Consistent Indentation (SHOULD be detected)")
    print("-" * 80)
    lines = [
        Line("• First bullet point", left=100, top=100, height=12),
        Line("• Second bullet point", left=101, top=115, height=12),  # Within tolerance
        Line("• Third bullet point", left=99, top=130, height=12),   # Within tolerance
    ]
    is_list, list_type, num_items = _detect_list_sequence(lines, 0, mapping)
    print(f"Lines: {[l.text for l in lines]}")
    print(f"Indents: {[l.left for l in lines]}")
    print(f"Result: {'✅ DETECTED' if is_list else '❌ NOT DETECTED'} as list ({num_items} items)")
    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✅ List detection now:")
    print("   • Excludes single-letter names (A. Smith)")
    print("   • Requires consecutive items for confirmation")
    print("   • Checks indentation consistency (±15pt tolerance)")
    print("   • Handles hyphens intelligently (not if followed by number)")
    print("   • Excludes Roman numeral I/i from patterns")
    print("   • Allows single strong bullets (•, ◦, ▪, etc.)")
    print()


if __name__ == "__main__":
    run_tests()
