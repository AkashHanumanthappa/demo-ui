# PR Guidance - What to Include

## What to Include in PR ✅

### Production Code (Must Include)

**1. pdf_to_excel_columns.py** ✅
- The only file with production code changes
- ~340 lines added
- Script detection integrated
- Ready for merge

---

## What NOT to Include in PR ❌

### Analysis Files (Local Use Only)

These were created for analysis and should stay local:

#### Original ColId Analysis Files
- ❌ `analyze_colid_weaving.py`
- ❌ `fix_colid_weaving.py`
- ❌ `test_colid_fix.py`
- ❌ `COLID_ANALYSIS_GUIDE.md`
- ❌ `COLID_DECISION_FLOWCHART.md`
- ❌ `COLID_WEAVING_SOLUTION.md`
- ❌ `COLID_WEAVING_VISUAL_EXAMPLE.md`
- ❌ `QUICK_START_COLID_FIX.md`
- ❌ `README_COLID_ANALYSIS.md`
- ❌ `START_HERE.md`
- ❌ `ANALYSIS_COMPLETE_SUMMARY.md`
- ❌ `ANALYSIS_DELIVERABLES.md`

#### Superscript Analysis Files
- ❌ `analyze_superscript_merge.py`
- ❌ `analyze_super_sub_correct.py`
- ❌ `fix_superscript_merge.py`
- ❌ `implement_script_detection.py`
- ❌ `SUPERSCRIPT_MERGE_ISSUE.md`
- ❌ `ROOT_CAUSE_ANALYSIS.md`
- ❌ `DEEPER_ANALYSIS_SUMMARY.md`
- ❌ `START_HERE_DEEPER_ANALYSIS.md`

#### Trade-off Analysis Files
- ❌ `BASELINE_VS_TOP_TRADEOFFS.md`
- ❌ `VISUAL_COMPARISON_BASELINE_TOP.md`
- ❌ `ANSWER_TO_YOUR_CONCERN.md`

#### Summary Files
- ❌ `FINAL_RECOMMENDATION.md`
- ❌ `IMPLEMENTATION_COMPLETE.md`
- ❌ `INTEGRATION_GUIDE.md`
- ❌ `QUICK_REFERENCE_PHASE1.md`
- ❌ `READY_FOR_PR.md`
- ❌ `CHANGES_SUMMARY_SCRIPT_DETECTION.md`
- ❌ `PR_GUIDANCE.md` (this file)
- ❌ `SUGGESTED_COMMIT_MESSAGE.txt`

**Reason**: These are analysis artifacts for local understanding, not production code.

---

## Optional: Documentation for Reviewers

If you want to help PR reviewers understand the change, you could include:

### Option 1: Inline Documentation Only
- Keep the comments in `pdf_to_excel_columns.py` (already included)
- Comments explain what Phase 1 and Phase 3 do
- Configuration constants are self-documenting

### Option 2: Add One Summary File
If reviewers need context, add just ONE file:

**`SCRIPT_DETECTION_README.md`** (create a clean version):
```markdown
# Superscript/Subscript Detection

## Problem
Superscripts (10⁷) and subscripts (H₂O) were not merging because 
baseline calculation fails for fragments with different heights.

## Solution
Three-phase detection:
1. Detect tiny fragments (w<15, h<12) using TOP position
2. Group rows using baseline (unchanged - preserves drop caps)
3. Merge scripts across rows

## Configuration
See constants at top of pdf_to_excel_columns.py (lines 19-27)

## Testing
Run on documents and verify:
- Terminal shows: "Detected N superscript(s)/subscript(s)"
- Excel shows: "10^7" not separate "10" and "7"
- Drop caps still separate (not merged)
```

---

## Suggested PR Contents

### Minimal PR (Recommended)
```
Files changed: 1
- pdf_to_excel_columns.py (340 lines added)

Commit message: Use SUGGESTED_COMMIT_MESSAGE.txt
```

### With Reviewer Context (Optional)
```
Files changed: 2
- pdf_to_excel_columns.py (340 lines added)
- SCRIPT_DETECTION_README.md (new - reviewer context)

Commit message: Use SUGGESTED_COMMIT_MESSAGE.txt
```

---

## Creating the PR

### Step 1: Check Git Status
```bash
git status
# Should show: modified: pdf_to_excel_columns.py
# Plus many untracked analysis files
```

### Step 2: Stage Only Production Code
```bash
# Stage ONLY the production file
git add pdf_to_excel_columns.py

# Optional: Add reviewer documentation
# git add SCRIPT_DETECTION_README.md

# Verify what's staged
git diff --staged
```

### Step 3: Commit
```bash
git commit -m "$(cat SUGGESTED_COMMIT_MESSAGE.txt)"

# Or write your own message
```

### Step 4: Push and Create PR
```bash
git push origin your-branch-name

# Then create PR in your Git UI
```

---

## Git Ignore Recommendations

Consider adding to `.gitignore`:

```
# Analysis files (local only)
analyze_*.py
fix_*.py
test_*.py
*ANALYSIS*.md
*WEAVING*.md
*COMPARISON*.md
*TRADEOFFS*.md
ANSWER_*.md
DEEPER_*.md
FINAL_*.md
IMPLEMENTATION_*.md
INTEGRATION_*.md
QUICK_*.md
READY_*.md
ROOT_*.md
START_HERE*.md
SUGGESTED_*.txt
CHANGES_SUMMARY*.md
PR_GUIDANCE.md
```

---

## Clean Up After PR

Once PR is merged, you can clean up analysis files:

```bash
# List analysis files
ls -1 *ANALYSIS*.md *WEAVING*.md analyze_*.py fix_*.py

# Remove them (AFTER PR is merged)
rm analyze_*.py fix_*.py test_*.py
rm *ANALYSIS*.md *WEAVING*.md *COMPARISON*.md
rm ANSWER_*.md DEEPER_*.md FINAL_*.md
rm IMPLEMENTATION_*.md INTEGRATION_*.md QUICK_*.md
rm READY_*.md ROOT_*.md START_HERE*.md
rm SUGGESTED_*.txt CHANGES_*.md PR_GUIDANCE.md
```

**Or keep them** for future reference if you might need to tune thresholds.

---

## Summary

**Include in PR**: 
- ✅ `pdf_to_excel_columns.py` (required)
- 🤔 `SCRIPT_DETECTION_README.md` (optional, for reviewers)

**Don't include in PR**:
- ❌ All analysis files (~30 files)
- ❌ Test scripts
- ❌ Documentation markdown files

**Reason**: As you said - "I want to do a deeper analysis" - these are analysis artifacts, not production code.

---

**Your PR is ready! Just `git add pdf_to_excel_columns.py` and commit.** 🚀
