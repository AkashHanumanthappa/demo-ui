const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs').promises;
const fsSync = require('fs');

/**
 * Execute RittDocConverter pipeline
 * @param {string} inputFilePath - Path to the input file (PDF or EPUB)
 * @param {string} outputDir - Directory for output files
 * @param {string} fileId - MongoDB file ID for WebSocket tracking
 * @returns {Promise<Object>} - Result object with output files info
 */
const executeConverter = async (inputFilePath, outputDir, fileId = null) => {
  return new Promise((resolve, reject) => {
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

    // Get paths
    const pythonPath = process.env.CONVERTER_PYTHON || 'python';
    const converterScriptPath = process.env.CONVERTER_SCRIPT_PATH ||
      path.join(__dirname, '../../RittDocConverter/integrated_pipeline.py');

    console.log('Starting conversion:', inputFilePath);

    const pyProcess = spawn(
      pythonPath,
      [converterScriptPath, inputFilePath, outputDir],
      { shell: true }
    );

    // Helper function to emit WebSocket events
    const emitProgress = (data) => {
      if (global.io && fileId) {
        global.io.emit('processing:progress', {
          fileId,
          message: data,
          timestamp: new Date().toISOString()
        });
      }
    };

    // Capture stdout and emit via WebSocket
    pyProcess.stdout.on('data', (data) => {
      const output = data.toString();

      // Keep existing console output
      process.stdout.write(output);

      // Emit to WebSocket
      emitProgress(output);

      // Extract and emit specific progress information
      const percentMatch = output.match(/(\d+\.\d+)%/);
      if (percentMatch && global.io && fileId) {
        const percentage = parseFloat(percentMatch[1]);
        console.log(`📊 [WS] Emitting percentage: ${percentage}% for fileId: ${fileId}`);
        global.io.emit('processing:percentage', {
          fileId,
          percentage,
          timestamp: new Date().toISOString()
        });
      }

      // Check for validation messages
      if (output.includes('DTD validation PASSED') && global.io && fileId) {
        console.log(`✅ [WS] Emitting validation message for fileId: ${fileId}`);
        global.io.emit('processing:validation', {
          fileId,
          message: output.trim(),
          timestamp: new Date().toISOString()
        });
      }
    });

    // Capture stderr and emit via WebSocket
    pyProcess.stderr.on('data', (data) => {
      const output = data.toString();

      // Keep existing console output
      process.stderr.write(output);

      // Emit errors/warnings to WebSocket
      if (global.io && fileId) {
        global.io.emit('processing:error', {
          fileId,
          message: output,
          timestamp: new Date().toISOString()
        });
      }
    });

    pyProcess.on('close', async (code) => {
      if (code !== 0) {
        return reject({
          success: false,
          message: 'Conversion failed',
          code
        });
      }

      try {
        const outputFiles = await getOutputFiles(outputDir);
        resolve({
          success: true,
          message: 'Document converted successfully',
          outputPath: outputDir,
          outputFiles
        });
      } catch (err) {
        reject({
          success: false,
          message: 'Error reading output files',
          error: err.message
        });
      }
    });
  });
};

/**
 * Get list of output files from directory
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
  getOutputFiles,
  cleanupFile,
  cleanupDirectory
};
