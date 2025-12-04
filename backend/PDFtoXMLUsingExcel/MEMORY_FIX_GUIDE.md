# Memory Issue Fix Guide

## Problem: "zsh: killed" Error

Your script is being killed by the operating system due to **Out of Memory (OOM)** conditions. This happens when:

1. The PDF processing requires more RAM than available
2. PyMuPDF + Camelot + Image extraction all compete for memory
3. Large PDFs at high DPI (200) consume 50-100MB+ per page

## Immediate Solutions

### Solution 1: Use Memory-Efficient Wrapper (RECOMMENDED)

Use the new `pdf_processor_memory_efficient.py` wrapper:

```bash
python3 pdf_processor_memory_efficient.py path/to/your.pdf
```

This wrapper will:
- Analyze your PDF and estimate memory requirements
- Auto-select optimal DPI
- Warn you if memory will be tight
- Provide better error messages

### Solution 2: Reduce DPI Manually

Lower DPI = less memory usage:

```bash
# Low memory systems
python3 pdf_to_unified_xml.py path/to/your.pdf --dpi 100 --full-pipeline

# Medium memory systems
python3 pdf_to_unified_xml.py path/to/your.pdf --dpi 150 --full-pipeline
```

**Memory usage by DPI:**
- DPI 100: ~25 MB per page
- DPI 150: ~50 MB per page
- DPI 200: ~100 MB per page (default)

### Solution 3: Check Available Memory

**On Mac:**
```bash
# Check memory usage
vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+([^:]+)[^\d]+(\d+)/ and printf("%-16s % 16.2f Mi\n", "$1:", $2 * $size / 1048576);'

# Or use Activity Monitor (GUI)
```

**On Linux:**
```bash
free -h
```

You need at least:
- **2GB free RAM** for small PDFs (< 50 pages)
- **4GB free RAM** for medium PDFs (50-200 pages)
- **8GB+ free RAM** for large PDFs (200+ pages)

### Solution 4: Process Without Full Pipeline

If you only need the unified XML (not DocBook), skip the pipeline:

```bash
python3 pdf_to_unified_xml.py path/to/your.pdf --dpi 150
```

This uses ~40% less memory by skipping font_roles_auto and heuristics.

## Long-Term Solutions

### 1. Add Swap Space (Linux/Mac)

Create swap file to use disk when RAM is full:

**Mac:**
```bash
# Mac automatically manages swap, but you can free memory:
sudo purge
```

**Linux:**
```bash
# Create 8GB swap file
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 2. Optimize Code for Chunked Processing

Modify `Multipage_Image_Extractor.py` to process pages in batches:

```python
# Process 10 pages at a time instead of all at once
BATCH_SIZE = 10
for start_page in range(0, page_count, BATCH_SIZE):
    end_page = min(start_page + BATCH_SIZE, page_count)
    # Process pages [start_page:end_page]
    gc.collect()  # Free memory between batches
```

### 3. Use Docker with Memory Limits

```bash
docker run --memory=8g --memory-swap=16g -v $(pwd):/workspace your-image \
    python3 pdf_to_unified_xml.py /workspace/input.pdf --dpi 150 --full-pipeline
```

## Monitoring Memory Usage

### Real-time Memory Monitor

```bash
# Mac
top -o MEM

# Linux
htop
# or
watch -n 1 free -h
```

### Profile Memory in Python

Add to your script:

```python
import tracemalloc
import gc

# At start of script
tracemalloc.start()

# After each major step
gc.collect()
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024**2:.1f}MB | Peak: {peak / 1024**2:.1f}MB")
```

## Diagnostic Commands

```bash
# 1. Check PDF info
python3 -c "import fitz; doc=fitz.open('your.pdf'); print(f'Pages: {len(doc)}'); doc.close()"

# 2. Check file size
ls -lh your.pdf

# 3. Test with minimal processing
python3 pdf_processor_memory_efficient.py your.pdf --no-pipeline --dpi 100

# 4. Monitor system while running
# In one terminal:
watch -n 1 'ps aux | grep python | grep -v grep'
# In another terminal:
python3 pdf_to_unified_xml.py your.pdf --dpi 100 --full-pipeline
```

## Quick Reference: What to Try

1. ✅ **Use wrapper script** (analyzes and adjusts automatically)
   ```bash
   python3 pdf_processor_memory_efficient.py path/to/your.pdf
   ```

2. ✅ **Reduce DPI to 100-150** (immediate 50-75% memory reduction)
   ```bash
   python3 pdf_to_unified_xml.py path/to/your.pdf --dpi 100 --full-pipeline
   ```

3. ✅ **Close other apps** (free up RAM)

4. ✅ **Check system memory** (ensure enough free RAM)
   ```bash
   free -h  # Linux
   vm_stat  # Mac
   ```

5. ⚠️ **Process on different machine** (if < 4GB RAM available)

## Expected Memory Usage

For a **100-page PDF**:

| DPI | Memory Required |
|-----|----------------|
| 100 | 2-3 GB |
| 150 | 4-5 GB |
| 200 | 8-10 GB |

For a **500-page PDF**:

| DPI | Memory Required |
|-----|----------------|
| 100 | 10-12 GB |
| 150 | 20-25 GB |
| 200 | 40-50 GB |

## Still Having Issues?

If you're still getting killed:

1. **Check the PDF file size**
   ```bash
   ls -lh *.pdf
   ```

2. **Check page count**
   ```bash
   python3 -c "import fitz; doc=fitz.open('your.pdf'); print(len(doc)); doc.close()"
   ```

3. **Try processing just 1 page** (to isolate the issue)
   - Extract first 10 pages to separate PDF
   - Process that smaller PDF
   - If successful, issue is memory-related

4. **Contact support with:**
   - PDF file size (MB)
   - PDF page count
   - Available system RAM
   - DPI being used
   - Where exactly it's being killed (check output)
