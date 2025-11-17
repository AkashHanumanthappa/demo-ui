const { exec } = require('child_process');
const path = require('path');
const fs = require('fs').promises;
const fsSync = require('fs');

/**
 * Execute RittDocConverter pipeline
 * @param {string} inputFilePath - Path to the input file (PDF or EPUB)
 * @param {string} outputDir - Directory for output files
 * @returns {Promise<Object>} - Result object with output files info
 */
const executeConverter = async (inputFilePath, outputDir) => {
  return new Promise((resolve, reject) => {
    // Ensure output directory exists
    if (!fsSync.existsSync(outputDir)) {
      fsSync.mkdirSync(outputDir, { recursive: true });
    }

    // Path to integrated_pipelines.py
    // Adjust this path based on where RittDocConverter is cloned
    const converterScriptPath = process.env.CONVERTER_SCRIPT_PATH ||
                                path.join(__dirname, '../../RittDocConverter/integrated_pipelines.py');

    // Python command with arguments
    // Adjust the command format based on actual integrated_pipelines.py requirements
    const command = `python3 "${converterScriptPath}" --input "${inputFilePath}" --output "${outputDir}"`;

    console.log('Executing conversion command:', command);

    exec(command, { maxBuffer: 1024 * 1024 * 10 }, async (error, stdout, stderr) => {
      if (error) {
        console.error('Conversion error:', error);
        console.error('stderr:', stderr);
        return reject({
          success: false,
          message: 'Document conversion failed',
          error: error.message,
          stderr: stderr
        });
      }

      try {
        // Read output directory to get generated files
        const outputFiles = await getOutputFiles(outputDir);

        resolve({
          success: true,
          message: 'Document converted successfully',
          outputPath: outputDir,
          outputFiles: outputFiles,
          stdout: stdout,
          stderr: stderr
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
  try {
    const files = await fs.readdir(dirPath, { withFileTypes: true });
    const outputFiles = [];

    for (const file of files) {
      if (file.isFile()) {
        const filePath = path.join(dirPath, file.name);
        const stats = await fs.stat(filePath);
        const ext = path.extname(file.name).toLowerCase();

        outputFiles.push({
          fileName: file.name,
          filePath: filePath,
          fileType: ext.replace('.', ''),
          fileSize: stats.size
        });
      } else if (file.isDirectory()) {
        // Recursively get files from subdirectories
        const subDirPath = path.join(dirPath, file.name);
        const subFiles = await getOutputFiles(subDirPath);
        outputFiles.push(...subFiles);
      }
    }

    return outputFiles;
  } catch (error) {
    console.error('Error reading directory:', error);
    return [];
  }
};

/**
 * Clean up uploaded file
 * @param {string} filePath - File path to delete
 */
const cleanupFile = async (filePath) => {
  try {
    await fs.unlink(filePath);
    console.log('Cleaned up file:', filePath);
  } catch (error) {
    console.error('Error cleaning up file:', error);
  }
};

/**
 * Clean up directory
 * @param {string} dirPath - Directory path to delete
 */
const cleanupDirectory = async (dirPath) => {
  try {
    await fs.rm(dirPath, { recursive: true, force: true });
    console.log('Cleaned up directory:', dirPath);
  } catch (error) {
    console.error('Error cleaning up directory:', error);
  }
};

module.exports = {
  executeConverter,
  getOutputFiles,
  cleanupFile,
  cleanupDirectory
};
