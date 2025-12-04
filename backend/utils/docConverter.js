const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs').promises;
const fsSync = require('fs');

/**
 * Execute appropriate converter based on file type
 * @param {string} inputFilePath - Path to the input file (PDF or EPUB)
 * @param {string} outputDir - Directory for output files
 * @returns {Promise<Object>} - Result object with output files info
 */
const executeConverter = async (inputFilePath, outputDir) => {
  return new Promise(async (resolve, reject) => {
    // Validate input
    if (!inputFilePath || typeof inputFilePath !== 'string') {
      return reject({ success: false, message: 'Invalid input file path' });
    }
    if (!outputDir || typeof outputDir !== 'string') {
      return reject({ success: false, message: 'Invalid output directory' });
    }
    if (!fsSync.existsSync(inputFilePath)) {
      return reject({ success: false, message: 'Input file not found', file: inputFilePath });
    }

    // Ensure output directory exists
    if (!fsSync.existsSync(outputDir)) {
      fsSync.mkdirSync(outputDir, { recursive: true });
    }

    // Get file extension
    const fileExtension = path.extname(inputFilePath).toLowerCase();
    
    console.log(`Detected file type: ${fileExtension}`);

    // Choose converter based on file type
    if (fileExtension === '.pdf') {
      // Use PDF pipeline
      console.log('Using PDF converter pipeline');
      return executePDFConverter(inputFilePath, outputDir)
        .then(resolve)
        .catch(reject);
    } else if (fileExtension === '.epub') {
      // Use EPUB pipeline (RittDocConverter)
      console.log('Using EPUB converter pipeline (RittDocConverter)');
      return executeEPUBConverter(inputFilePath, outputDir)
        .then(resolve)
        .catch(reject);
    } else {
      return reject({
        success: false,
        message: `Unsupported file type: ${fileExtension}. Only PDF and EPUB are supported.`
      });
    }
  });
};

/**
 * Execute PDF to XML converter pipeline
 * @param {string} inputFilePath - Path to the PDF file
 * @param {string} outputDir - Directory for output files
 * @returns {Promise<Object>} - Result object with output files info
 */
const executePDFConverter = async (inputFilePath, outputDir) => {
  return new Promise((resolve, reject) => {
    // PDF pipeline directory (relative to backend folder)
    const pdfPipelineDir = process.env.PDF_CONVERTER_DIR ||
      path.join(__dirname, '..', 'PDFtoXMLUsingExcel');

    // Python executable - default to python3 (for Linux/AWS) or resolve from venv on Windows
    const pythonPath = process.env.PDF_CONVERTER_PYTHON ||
      (process.platform === 'win32'
        ? path.join(pdfPipelineDir, 'venv', 'Scripts', 'python.exe')
        : 'python3');
    
    // Main script name (just the filename, NOT a path)
    const scriptName = process.env.PDF_CONVERTER_SCRIPT || 'pdf_to_unified_xml.py';
    
    // Build the full script path correctly
    const converterScriptPath = path.join(pdfPipelineDir, scriptName);

    console.log('═══════════════════════════════════════════');
    console.log('Starting PDF Conversion Pipeline');
    console.log('═══════════════════════════════════════════');
    console.log('Input file:', inputFilePath);
    console.log('Output directory:', outputDir);
    console.log('Python path:', pythonPath);
    console.log('Script path:', converterScriptPath);
    console.log('Working directory:', pdfPipelineDir);
    console.log('═══════════════════════════════════════════');

    // Check if Python executable exists
    if (!fsSync.existsSync(pythonPath)) {
      console.error('❌ Python executable not found!');
      console.error('Looking for:', pythonPath);
      return reject({
        success: false,
        message: 'Python executable not found in virtual environment',
        path: pythonPath
      });
    }

    // Check if PDF converter script exists
    if (!fsSync.existsSync(converterScriptPath)) {
      console.error('❌ PDF converter script not found!');
      console.error('Looking for:', converterScriptPath);
      return reject({
        success: false,
        message: 'PDF converter script not found',
        path: converterScriptPath
      });
    }

    // Build command arguments
    const args = [
      scriptName,
      inputFilePath,
      '--full-pipeline',
      '--out',
      outputDir
    ];

    console.log('Command:', pythonPath, args.join(' '));
    console.log('Full command line:', `${pythonPath} ${args.join(' ')}`);

    // Spawn Python process with UTF-8 encoding
    const pyProcess = spawn(
      pythonPath,
      args,
      { 
        cwd: pdfPipelineDir,
        shell: true,
        env: {
          ...process.env,
          PYTHONIOENCODING: 'utf-8',
          PYTHONUTF8: '1'
        }
      }
    );

    let stdout = '';
    let stderr = '';

    pyProcess.stdout.on('data', (data) => {
      const output = data.toString('utf8');
      stdout += output;
      console.log(`[PDF Pipeline] ${output.trim()}`);
    });

    pyProcess.stderr.on('data', (data) => {
      const output = data.toString('utf8');
      stderr += output;
      console.error(`[PDF Pipeline Error] ${output.trim()}`);
    });

    pyProcess.on('close', async (code) => {
      console.log('═══════════════════════════════════════════');
      console.log(`PDF Pipeline finished with exit code: ${code}`);
      console.log('═══════════════════════════════════════════');

      if (code !== 0) {
        console.error('❌ PDF conversion failed!');
        console.error('Exit code:', code);
        if (stderr) console.error('Error output:', stderr);
        
        return reject({
          success: false,
          message: 'PDF conversion failed',
          code,
          stderr: stderr || 'No error output',
          stdout: stdout || 'No output'
        });
      }

      try {
        const pdfBaseName = path.basename(inputFilePath, '.pdf');
        const pdfDir = path.dirname(inputFilePath);
        
        console.log('\n🔍 Collecting Final Outputs...');
        
        // Ensure output directory exists
        if (!fsSync.existsSync(outputDir)) {
          fsSync.mkdirSync(outputDir, { recursive: true });
        }
        
        const outputFiles = [];
        
        // ========== EXACTLY the 5 files from "Final Outputs" ==========
        const finalOutputs = [
          // 1. Unified XML
          { 
            source: path.join(pdfDir, `${pdfBaseName}_unified.xml`),
            name: `${pdfBaseName}_unified.xml`,
            label: 'Unified XML'
          },
          // 2. Font Roles
          { 
            source: path.join(pdfDir, `${pdfBaseName}_font_roles.json`),
            name: `${pdfBaseName}_font_roles.json`,
            label: 'Font Roles'
          },
          // 3. Structured XML
          { 
            source: path.join(pdfDir, `${pdfBaseName}_structured.xml`),
            name: `${pdfBaseName}_structured.xml`,
            label: 'Structured XML'
          },
          // 4. Package ZIP (pre-validation)
          { 
            source: path.join(pdfDir, `${pdfBaseName}_package`, `${pdfBaseName}_structured.zip`),
            name: `${pdfBaseName}_structured.zip`,
            label: 'Package ZIP (pre-validation)'
          },
          // 5. Validated ZIP (RittDoc compliant)
          { 
            source: path.join(pdfDir, `${pdfBaseName}_package`, `${pdfBaseName}_rittdoc.zip`),
            name: `${pdfBaseName}_rittdoc.zip`,
            label: 'Validated ZIP (RittDoc compliant)'
          }
        ];
        
        console.log('\nFinal Outputs:');
        
        // ========== Copy ONLY these 5 files ==========
        for (const file of finalOutputs) {
          if (fsSync.existsSync(file.source)) {
            const stats = fsSync.statSync(file.source);
            const destPath = path.join(outputDir, file.name);
            
            // Copy file
            fsSync.copyFileSync(file.source, destPath);
            console.log(`  - ${file.label}: ${file.source}`);
            
            const ext = path.extname(file.name).toLowerCase();
            outputFiles.push({
              fileName: file.name,
              filePath: destPath,
              fileType: ext.replace('.', ''),
              fileSize: stats.size
            });
          } else {
            console.log(`  ⚠ ${file.label}: NOT FOUND (${file.source})`);
          }
        }
        
        // ========== Validation ==========
        if (outputFiles.length === 0) {
          console.warn('\n⚠️ No output files found!');
          return reject({
            success: false,
            message: 'No output files generated by PDF converter',
            stdout,
            stderr
          });
        }
        
        // ========== Summary ==========
        console.log(`\n✅ Successfully collected ${outputFiles.length} files`);
        console.log('\n📦 Files ready for upload:');
        outputFiles.forEach(f => {
          const sizeMB = (f.fileSize / 1024 / 1024).toFixed(2);
          const sizeKB = (f.fileSize / 1024).toFixed(2);
          const sizeStr = f.fileSize > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;
          console.log(`  - ${f.fileName} (${f.fileType}, ${sizeStr})`);
        });
        
        const totalSize = outputFiles.reduce((sum, f) => sum + f.fileSize, 0);
        console.log(`\n📊 Total: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
        
        resolve({
          success: true,
          message: 'PDF converted successfully',
          outputPath: outputDir,
          outputFiles,
          converterType: 'PDFtoXML'
        });
      } catch (err) {
        console.error('❌ Error processing PDF output files:', err);
        console.error('Stack trace:', err.stack);
        reject({
          success: false,
          message: 'Error processing PDF output files',
          error: err.message
        });
      }
    });

    pyProcess.on('error', (error) => {
      console.error('❌ Failed to start PDF converter process:', error);
      reject({
        success: false,
        message: 'Failed to start PDF converter process',
        error: error.message
      });
    });
  });
};

/**
 * Execute EPUB converter pipeline (RittDocConverter)
 * @param {string} inputFilePath - Path to the EPUB file
 * @param {string} outputDir - Directory for output files
 * @returns {Promise<Object>} - Result object with output files info
 */
const executeEPUBConverter = async (inputFilePath, outputDir) => {
  return new Promise((resolve, reject) => {
    // Get paths (relative to backend folder)
    const pythonPath = process.env.CONVERTER_PYTHON ||
      (process.platform === 'win32'
        ? path.join(__dirname, '..', 'RittDocConverter', 'venv', 'Scripts', 'python.exe')
        : 'python3');
    const converterScriptPath = process.env.CONVERTER_SCRIPT_PATH ||
      path.join(__dirname, '..', 'RittDocConverter', 'integrated_pipeline.py');

    console.log('═══════════════════════════════════════════');
    console.log('Starting EPUB Conversion Pipeline (RittDocConverter)');
    console.log('═══════════════════════════════════════════');
    console.log('Input file:', inputFilePath);
    console.log('Output directory:', outputDir);
    console.log('Python path:', pythonPath);
    console.log('Script path:', converterScriptPath);
    console.log('═══════════════════════════════════════════');

    // Check if EPUB converter script exists
    if (!fsSync.existsSync(converterScriptPath)) {
      console.error('❌ EPUB converter script not found!');
      return reject({
        success: false,
        message: 'EPUB converter script not found',
        path: converterScriptPath
      });
    }

    const pyProcess = spawn(
      pythonPath,
      [converterScriptPath, inputFilePath, outputDir],
      { shell: true }
    );

    let stdout = '';
    let stderr = '';

    pyProcess.stdout.on('data', (data) => {
      const output = data.toString();
      stdout += output;
      console.log(`[EPUB Pipeline] ${output.trim()}`);
    });

    pyProcess.stderr.on('data', (data) => {
      const output = data.toString();
      stderr += output;
      console.error(`[EPUB Pipeline Error] ${output.trim()}`);
    });

    pyProcess.on('close', async (code) => {
      console.log('═══════════════════════════════════════════');
      console.log(`EPUB Pipeline finished with exit code: ${code}`);
      console.log('═══════════════════════════════════════════');

      if (code !== 0) {
        console.error('❌ EPUB conversion failed!');
        console.error('Exit code:', code);
        if (stderr) console.error('Error output:', stderr);
        
        return reject({
          success: false,
          message: 'EPUB conversion failed',
          code,
          stderr: stderr || 'No error output',
          stdout: stdout || 'No output'
        });
      }

      try {
        const outputFiles = await getOutputFiles(outputDir);
        
        if (outputFiles.length === 0) {
          console.warn('⚠️ No output files generated');
          return reject({
            success: false,
            message: 'No output files generated by EPUB converter',
            stdout,
            stderr
          });
        }

        console.log(`✅ EPUB conversion completed successfully!`);
        console.log(`Generated ${outputFiles.length} output files:`);
        outputFiles.forEach(f => console.log(`  - ${f.fileName} (${f.fileType}, ${(f.fileSize / 1024).toFixed(2)} KB)`));
        
        resolve({
          success: true,
          message: 'EPUB converted successfully',
          outputPath: outputDir,
          outputFiles,
          converterType: 'RittDocConverter'
        });
      } catch (err) {
        console.error('❌ Error reading EPUB output files:', err);
        reject({
          success: false,
          message: 'Error reading EPUB output files',
          error: err.message
        });
      }
    });

    pyProcess.on('error', (error) => {
      console.error('❌ Failed to start EPUB converter process:', error);
      reject({
        success: false,
        message: 'Failed to start EPUB converter process',
        error: error.message
      });
    });
  });
};

/**
 * Get list of output files from directory (recursively)
 * @param {string} dirPath - Directory path
 * @returns {Promise<Array>} - Array of file objects
 */
const getOutputFiles = async (dirPath) => {
  const files = await fs.readdir(dirPath, { withFileTypes: true });
  let outputFiles = [];

  for (const file of files) {
    const fullPath = path.join(dirPath, file.name);
    if (file.isFile()) {
      const stats = await fs.stat(fullPath);
      const ext = path.extname(file.name).toLowerCase();
      outputFiles.push({
        fileName: file.name,
        filePath: fullPath,
        fileType: ext.replace('.', ''),
        fileSize: stats.size
      });
    } else if (file.isDirectory()) {
      // Recursively get files from subdirectories
      const subFiles = await getOutputFiles(fullPath);
      outputFiles = outputFiles.concat(subFiles);
    }
  }

  return outputFiles;
};

/**
 * Delete a file
 * @param {string} filePath
 */
const cleanupFile = async (filePath) => {
  try {
    await fs.unlink(filePath);
    console.log('Cleaned up file:', filePath);
  } catch (err) {
    console.error('Error cleaning up file:', err);
  }
};

/**
 * Delete a directory recursively
 * @param {string} dirPath
 */
const cleanupDirectory = async (dirPath) => {
  try {
    await fs.rm(dirPath, { recursive: true, force: true });
    console.log('Cleaned up directory:', dirPath);
  } catch (err) {
    console.error('Error cleaning up directory:', err);
  }
};

module.exports = {
  executeConverter,
  executePDFConverter,
  executeEPUBConverter,
  getOutputFiles,
  cleanupFile,
  cleanupDirectory
};