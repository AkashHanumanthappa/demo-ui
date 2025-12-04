# Quick Fix for "zsh: killed" Error

## The Problem
Your script is being killed by the OS due to **Out of Memory (OOM)**.

## Immediate Solution (Pick One)

### ✅ Option 1: Use the New Wrapper (EASIEST)
```bash
python3 pdf_processor_memory_efficient.py path/to/your.pdf
```

This automatically:
- Analyzes your PDF
- Selects optimal DPI
- Warns if memory is tight
- Runs with memory optimization

### ✅ Option 2: Reduce DPI Manually
```bash
# For large PDFs (saves 50-75% memory)
python3 pdf_to_unified_xml.py path/to/your.pdf --dpi 100 --full-pipeline

# For medium PDFs
python3 pdf_to_unified_xml.py path/to/your.pdf --dpi 150 --full-pipeline
```

### ✅ Option 3: Diagnose First
```bash
python3 diagnose_pdf.py path/to/your.pdf
```

This shows you:
- Exact memory requirements
- Recommended DPI
- Suggested commands
- Whether your system can handle it

## What Changed

I've created 3 new tools for you:

1. **`pdf_processor_memory_efficient.py`** - Smart wrapper that handles everything
2. **`diagnose_pdf.py`** - Analyzes PDFs and estimates memory needs
3. **`MEMORY_FIX_GUIDE.md`** - Complete troubleshooting guide

I also optimized `pdf_to_unified_xml.py` by adding garbage collection between steps.

## Quick Test

Try diagnosing one of your PDFs:
```bash
python3 diagnose_pdf.py 9780803694958.pdf
```

Then run with recommended settings:
```bash
python3 pdf_processor_memory_efficient.py 9780803694958.pdf
```

## Memory Usage by DPI

| DPI | Quality | Memory per 100 pages |
|-----|---------|---------------------|
| 200 | High    | ~10 GB              |
| 150 | Medium  | ~5 GB               |
| 100 | Low     | ~2.5 GB             |

**Lower DPI = Less memory but lower image quality**

For most book PDFs, DPI 150 is a good balance.

## Still Having Issues?

1. Check available memory:
   ```bash
   # Mac
   vm_stat
   
   # Linux  
   free -h
   ```

2. Close other applications

3. Try processing just the unified XML (skips DocBook):
   ```bash
   python3 pdf_to_unified_xml.py path/to/your.pdf --dpi 150
   ```

4. See `MEMORY_FIX_GUIDE.md` for advanced solutions
