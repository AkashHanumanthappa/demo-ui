#!/bin/bash
################################################################################
# Automated DTD Error Fixing Workflow
#
# This script runs the complete error analysis and fixing workflow:
#   1. Analyze remaining errors
#   2. Apply targeted fixes
#   3. Re-validate with compliance pipeline
#   4. Report results
#
# Usage:
#   ./fix_remaining_errors_workflow.sh <input_package.zip>
#
# Or with custom output:
#   ./fix_remaining_errors_workflow.sh <input_package.zip> <output_package.zip>
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check arguments
if [ $# -lt 1 ]; then
    print_error "Usage: $0 <input_package.zip> [output_package.zip]"
    echo ""
    echo "Example:"
    echo "  $0 9780989163286_rittdoc.zip"
    echo "  $0 9780989163286_rittdoc.zip 9780989163286_final.zip"
    exit 1
fi

INPUT_ZIP="$1"
if [ ! -f "$INPUT_ZIP" ]; then
    print_error "Input file not found: $INPUT_ZIP"
    exit 1
fi

# Determine output paths
INPUT_DIR=$(dirname "$INPUT_ZIP")
INPUT_NAME=$(basename "$INPUT_ZIP" .zip)

if [ $# -ge 2 ]; then
    OUTPUT_ZIP="$2"
else
    OUTPUT_ZIP="${INPUT_DIR}/${INPUT_NAME}_final.zip"
fi

TARGETED_ZIP="${INPUT_DIR}/${INPUT_NAME}_targeted_fix.zip"

# DTD path
DTD_PATH="RITTDOCdtd/v1.1/RittDocBook.dtd"
if [ ! -f "$DTD_PATH" ]; then
    print_warning "DTD not found at $DTD_PATH, will use default path in scripts"
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header "DTD ERROR FIXING WORKFLOW"
echo "Input:  $INPUT_ZIP"
echo "Output: $OUTPUT_ZIP"
echo ""
print_info "This workflow will:"
echo "  1. Analyze remaining errors"
echo "  2. Apply targeted fixes"
echo "  3. Re-validate with full pipeline"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

################################################################################
# STEP 1: ANALYZE ERRORS
################################################################################
print_header "STEP 1: ANALYZING REMAINING ERRORS"

if ! python3 "$SCRIPT_DIR/analyze_remaining_errors.py" "$INPUT_ZIP" 2>&1 | tee /tmp/analyze_output.txt; then
    print_warning "Analysis completed with warnings"
else
    print_success "Analysis completed"
fi

# Extract error count from analysis
ERROR_COUNT=$(grep -oP "Total errors: \K\d+" /tmp/analyze_output.txt | head -1 || echo "unknown")
print_info "Found $ERROR_COUNT total errors"

echo ""
read -p "Press Enter to continue with fixes or Ctrl+C to cancel..."

################################################################################
# STEP 2: APPLY TARGETED FIXES
################################################################################
print_header "STEP 2: APPLYING TARGETED FIXES"

if ! python3 "$SCRIPT_DIR/targeted_dtd_fixer.py" "$INPUT_ZIP" "$TARGETED_ZIP" 2>&1 | tee /tmp/fix_output.txt; then
    print_error "Targeted fixes failed"
    exit 1
fi

# Extract fix statistics
FIXES_APPLIED=$(grep -oP "Total fixes: \K\d+" /tmp/fix_output.txt | tail -1 || echo "unknown")
print_success "Applied $FIXES_APPLIED fix(es)"
print_info "Intermediate package: $TARGETED_ZIP"

echo ""
read -p "Press Enter to continue with validation or Ctrl+C to cancel..."

################################################################################
# STEP 3: RE-VALIDATE WITH COMPLIANCE PIPELINE
################################################################################
print_header "STEP 3: RE-VALIDATING WITH COMPLIANCE PIPELINE"

if ! python3 "$SCRIPT_DIR/rittdoc_compliance_pipeline.py" "$TARGETED_ZIP" --output "$OUTPUT_ZIP" --iterations 2 2>&1 | tee /tmp/validate_output.txt; then
    print_warning "Validation completed with warnings"
else
    print_success "Validation completed"
fi

# Extract final statistics
FINAL_ERRORS=$(grep -oP "Final errors:\s+\K\d+" /tmp/validate_output.txt | tail -1 || echo "unknown")
TOTAL_FIXES=$(grep -oP "Total fixes applied:\s+\K\d+" /tmp/validate_output.txt | tail -1 || echo "unknown")
IMPROVEMENT=$(grep -oP "Improvement:\s+\K[\d.]+%" /tmp/validate_output.txt | tail -1 || echo "unknown")

################################################################################
# STEP 4: REPORT RESULTS
################################################################################
print_header "WORKFLOW COMPLETE"

echo "Summary:"
echo "  Initial errors:    $ERROR_COUNT"
echo "  Targeted fixes:    $FIXES_APPLIED"
echo "  Pipeline fixes:    $TOTAL_FIXES"
echo "  Final errors:      $FINAL_ERRORS"
echo "  Improvement:       $IMPROVEMENT"
echo ""
echo "Output files:"
echo "  Targeted fix ZIP:  $TARGETED_ZIP"
echo "  Final package:     $OUTPUT_ZIP"
echo ""

# Provide recommendations based on results
if [ "$FINAL_ERRORS" != "unknown" ]; then
    if [ "$FINAL_ERRORS" -eq 0 ]; then
        print_success "Perfect! All errors resolved!"
        echo "Your package is now fully DTD compliant."
    elif [ "$FINAL_ERRORS" -lt 20 ]; then
        print_success "Excellent! Only $FINAL_ERRORS errors remaining."
        echo "Recommendation: Proceed with manual fixes for remaining errors."
        echo "See ERROR_FIXING_WORKFLOW.md for manual fix examples."
    elif [ "$FINAL_ERRORS" -lt 50 ]; then
        print_warning "Good progress! $FINAL_ERRORS errors remaining."
        echo "Recommendation: Run one more iteration of this workflow."
        echo "Command: $0 \"$OUTPUT_ZIP\" \"${INPUT_DIR}/${INPUT_NAME}_iteration2.zip\""
    elif [ "$FINAL_ERRORS" -lt 100 ]; then
        print_warning "Moderate progress. $FINAL_ERRORS errors remaining."
        echo "Recommendation: Analyze error patterns and run another iteration."
        echo "Command: python3 analyze_remaining_errors.py \"$OUTPUT_ZIP\""
    else
        print_warning "Limited progress. $FINAL_ERRORS errors remaining."
        echo "Recommendation: Review detailed analysis for custom fix strategy."
        echo "The errors may require specialized fixes beyond the automated tools."
    fi
else
    print_info "Could not determine final error count from output."
    echo "Please check the validation report manually."
fi

echo ""
print_header "NEXT STEPS"
echo "1. Review the validation report:"
echo "   - Check the generated Excel file for detailed error breakdown"
echo ""
echo "2. If errors remain:"
echo "   - Run analysis: python3 analyze_remaining_errors.py \"$OUTPUT_ZIP\""
echo "   - Review: ERROR_FIXING_WORKFLOW.md for manual fix guidance"
echo ""
echo "3. For manual fixes:"
echo "   - Extract package: unzip \"$OUTPUT_ZIP\" -d extracted/"
echo "   - Edit files as needed"
echo "   - Re-zip: cd extracted && zip -r ../fixed.zip ."
echo "   - Validate: python3 validate_with_entity_tracking.py fixed.zip"

print_header "WORKFLOW FINISHED"
