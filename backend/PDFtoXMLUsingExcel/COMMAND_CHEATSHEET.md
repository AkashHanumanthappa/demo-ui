# PDF Processing Command Cheatsheet

## 🚨 Your Original Command (FAILED)
```bash
python3 pdf_to_unified_xml.py --full-pipeline
# ❌ KILLED - Out of Memory
```

## ✅ NEW Commands (Use These Instead)

### Best Option: Smart Wrapper
```bash
# Automatically handles everything
python3 pdf_processor_memory_efficient.py YOUR_PDF_FILE.pdf
```

### Quick Commands by Memory Situation

#### Have 8GB+ RAM Available
```bash
python3 pdf_to_unified_xml.py YOUR_PDF_FILE.pdf --dpi 150 --full-pipeline
```

#### Have 4-8GB RAM Available
```bash
python3 pdf_to_unified_xml.py YOUR_PDF_FILE.pdf --dpi 100 --full-pipeline
```

#### Have < 4GB RAM Available
```bash
# Skip DocBook processing to save memory
python3 pdf_to_unified_xml.py YOUR_PDF_FILE.pdf --dpi 100
```

## 📊 Diagnose First (Recommended)

```bash
# Shows memory requirements and recommendations
python3 diagnose_pdf.py YOUR_PDF_FILE.pdf
```

## 🔍 Check Your System

### Check Available Memory
```bash
# Mac
vm_stat

# Linux
free -h
```

### Monitor While Processing
```bash
# Open Activity Monitor (Mac) or run:
watch -n 1 'vm_stat'
```

## 📁 Your Specific Case

Based on your error, run:
```bash
# Replace with your actual PDF path
PDF="/Users/jagadishchowdibegurumesh/Documents/Zentrovia/Accounts/R2/Publisher_Input/Shellock/9780989163286.pdf"

# Option 1: Smart wrapper (recommended)
python3 pdf_processor_memory_efficient.py "$PDF"

# Option 2: Direct with lower DPI
python3 pdf_to_unified_xml.py "$PDF" --dpi 150 --full-pipeline

# Option 3: Lowest memory usage
python3 pdf_to_unified_xml.py "$PDF" --dpi 100 --full-pipeline
```

## 🎯 DPI Selection Guide

| Your RAM | Recommended DPI | Command |
|----------|----------------|---------|
| < 4 GB   | 100            | `--dpi 100` |
| 4-8 GB   | 100-150        | `--dpi 150` |
| 8-16 GB  | 150-200        | `--dpi 150` |
| 16+ GB   | 200 (default)  | `--dpi 200` |

## 🛠️ Troubleshooting Commands

```bash
# 1. Check if PDF is valid
python3 -c "import fitz; doc=fitz.open('YOUR_PDF_FILE.pdf'); print(f'{len(doc)} pages'); doc.close()"

# 2. Check file size
ls -lh YOUR_PDF_FILE.pdf

# 3. Run diagnostic
python3 diagnose_pdf.py YOUR_PDF_FILE.pdf

# 4. Test with minimal processing
python3 pdf_to_unified_xml.py YOUR_PDF_FILE.pdf --dpi 100
```

## 📚 Which Guide to Read?

- **Just want it fixed:** Read `QUICK_FIX.md`
- **Want to understand:** Read `SOLUTION_MEMORY_ISSUE.md`
- **Having issues:** Read `MEMORY_FIX_GUIDE.md`
- **Quick reference:** This file

## ⚡ One-Liner Solutions

```bash
# Diagnose and tell me what to do
python3 diagnose_pdf.py YOUR_PDF_FILE.pdf

# Just fix it automatically
python3 pdf_processor_memory_efficient.py YOUR_PDF_FILE.pdf

# Manual fix with low memory
python3 pdf_to_unified_xml.py YOUR_PDF_FILE.pdf --dpi 100 --full-pipeline
```

## 🎓 Remember

- **Lower DPI = Less Memory** (but lower image quality)
- **DPI 150 is usually the best balance**
- **Close other apps** before processing large PDFs
- **Check available RAM first** to avoid wasting time
- **Use the wrapper** - it handles everything automatically

---

**Copy-paste this command:**

```bash
python3 pdf_processor_memory_efficient.py /Users/jagadishchowdibegurumesh/Documents/Zentrovia/Accounts/R2/Publisher_Input/Shellock/9780989163286.pdf
```

Replace the path with your actual PDF file path.
