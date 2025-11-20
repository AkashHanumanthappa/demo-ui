const File = require('../models/File');
const path = require('path');
const fs = require('fs');
const { executeConverter, cleanupFile, cleanupDirectory } = require('../utils/docConverter');
const {
  uploadFileToGridFS,
  uploadMultipleToGridFS,
  deleteFromGridFS,
  downloadFromGridFS,
  downloadToLocal
} = require('../utils/gridfs');

// @desc    Upload and process file
// @route   POST /api/files/upload
// @access  Private
const uploadFile = async (req, res) => {
  let tempFilePath = null;
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, message: 'No file uploaded' });
    }

    const { originalname, filename, path: filePath, size, mimetype } = req.file;
    const fileType = path.extname(originalname).toLowerCase().replace('.', '');
    tempFilePath = filePath;

    console.log(`Uploading file to GridFS: ${originalname}`);

    // Upload file to GridFS
    const gridfsResult = await uploadFileToGridFS(req.file, {
      uploadedBy: req.user._id,
      fileType: fileType
    });

    console.log(`File uploaded to GridFS with ID: ${gridfsResult.fileId}`);

    // Save file record in DB with GridFS reference
    const file = await File.create({
      originalName: originalname,
      fileName: filename,
      filePath: null,  // Not using local storage anymore
      gridfsInputFileId: gridfsResult.fileId,
      storedInGridFS: true,
      fileType: fileType,
      fileSize: size,
      mimeType: mimetype,
      uploadedBy: req.user._id,
      status: 'uploaded'
    });

    // Clean up temporary uploaded file
    await cleanupFile(tempFilePath);
    console.log(`Cleaned up temporary file: ${tempFilePath}`);

    // Start async processing (don't wait for it to complete)
    processFileAsync(file);

    // Return immediate response - processing will continue in background
    res.status(200).json({
      success: true,
      message: 'File uploaded successfully, processing started',
      data: { file }
    });
  } catch (error) {
    // Clean up temporary file in case of error
    if (tempFilePath) {
      await cleanupFile(tempFilePath);
    }

    res.status(500).json({
      success: false,
      message: 'Error uploading file',
      error: error.message
    });
  }
};

// @desc    Process file asynchronously
const processFileAsync = async (file) => {
  let tempInputPath = null;
  let outputDir = null;

  try {
    // Validate file object
    if (!file || !file._id || !file.gridfsInputFileId) {
      console.error('Invalid file object passed to processFileAsync:', file);
      throw new Error('Invalid file object - missing GridFS input file ID');
    }

    // Update status to processing
    await file.updateStatus('processing');

    // Create temporary directory for this file's processing
    const tempDir = path.join(__dirname, '../temp', file._id.toString());
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    // Download input file from GridFS to temporary location
    tempInputPath = path.join(tempDir, file.originalName);
    console.log(`Downloading input file from GridFS to: ${tempInputPath}`);
    await downloadToLocal(file.gridfsInputFileId, tempInputPath);
    console.log(`Input file downloaded successfully`);

    // Create output directory for this file
    outputDir = path.join(tempDir, 'output');

    const fileIdString = file._id.toString();
    console.log(`Processing file ${fileIdString}: ${file.originalName}`);

    // Emit processing started event via WebSocket
    if (global.io) {
      console.log(`🚀 [WS] Emitting processing:started for fileId: ${fileIdString}`);
      global.io.emit('processing:started', {
        fileId: fileIdString,
        fileName: file.originalName,
        timestamp: new Date().toISOString()
      });

      // Emit a test percentage to verify WebSocket is working
      console.log(`🧪 [WS] Emitting test percentage: 0% for fileId: ${fileIdString}`);
      global.io.emit('processing:percentage', {
        fileId: fileIdString,
        percentage: 0,
        timestamp: new Date().toISOString()
      });
    }

    // Execute converter with fileId for WebSocket tracking
    console.log(`🔧 Executing converter with fileId: ${fileIdString}`);
    const result = await executeConverter(tempInputPath, outputDir, fileIdString);

    // Upload output files to GridFS
    console.log(`Uploading ${result.outputFiles.length} output files to GridFS...`);
    const gridfsFiles = await uploadMultipleToGridFS(
      result.outputFiles,
      {
        sourceFileId: file._id,
        uploadedBy: file.uploadedBy,
        conversionType: 'RittDocConverter'
      }
    );

    // Map GridFS file info to output files array (no local filePath)
    const outputFilesWithGridFS = result.outputFiles.map((file, index) => ({
      fileName: file.fileName,
      filePath: null,  // Not storing local path anymore
      fileType: file.fileType,
      fileSize: file.fileSize,
      gridfsFileId: gridfsFiles[index].fileId,
      storedInGridFS: true
    }));

    // Update file record with results (no outputPath)
    await file.updateStatus('completed', {
      outputPath: null,  // Not using local storage anymore
      outputFiles: outputFilesWithGridFS,
      conversionMetadata: {
        conversionType: 'RittDocConverter',
        outputFormats: result.outputFiles.map(f => f.fileType)
      }
    });

    console.log(`File ${file._id} processed successfully and uploaded to GridFS`);

    // Emit processing completed event via WebSocket
    if (global.io) {
      // Emit 100% before completion
      console.log(`🎯 [WS] Emitting final percentage: 100% for fileId: ${fileIdString}`);
      global.io.emit('processing:percentage', {
        fileId: fileIdString,
        percentage: 100,
        timestamp: new Date().toISOString()
      });

      console.log(`🎉 [WS] Emitting processing:completed for fileId: ${fileIdString}`);
      global.io.emit('processing:completed', {
        fileId: fileIdString,
        fileName: file.originalName,
        timestamp: new Date().toISOString()
      });
    }

    // Clean up all temporary files
    try {
      await cleanupDirectory(tempDir);
      console.log(`Cleaned up temporary directory: ${tempDir}`);
    } catch (cleanupError) {
      console.error('Error cleaning up temporary directory:', cleanupError);
      // Don't fail the process if cleanup fails
    }

  } catch (error) {
    console.error(`File processing failed:`, error);

    // Clean up temporary files in case of error
    if (outputDir) {
      try {
        const tempDir = path.dirname(outputDir);
        await cleanupDirectory(tempDir);
        console.log(`Cleaned up temporary directory after error: ${tempDir}`);
      } catch (cleanupError) {
        console.error('Error cleaning up temporary directory after error:', cleanupError);
      }
    }

    // Try to update status to failed if file object is valid
    if (file && file.updateStatus) {
      try {
        await file.updateStatus('failed', {
          errorMessage: error.message || error.error || 'Conversion failed'
        });

        // Emit processing failed event via WebSocket
        if (global.io) {
          global.io.emit('processing:failed', {
            fileId: file._id.toString(),
            fileName: file.originalName,
            error: error.message || error.error || 'Conversion failed',
            timestamp: new Date().toISOString()
          });
        }
      } catch (updateError) {
        console.error('Failed to update file status:', updateError);
      }
    }
  }
};

// @desc    Get all files for current user
// @route   GET /api/files
// @access  Private
const getUserFiles = async (req, res) => {
  try {
    const files = await File.find({ uploadedBy: req.user._id })
      .sort({ createdAt: -1 })
      .populate('uploadedBy', 'username email');

    res.status(200).json({
      success: true,
      count: files.length,
      data: { files }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Error fetching files',
      error: error.message
    });
  }
};

// @desc    Get all files (Admin only)
// @route   GET /api/files/all
// @access  Private/Admin
const getAllFiles = async (req, res) => {
  try {
    const files = await File.find()
      .sort({ createdAt: -1 })
      .populate('uploadedBy', 'username email');

    res.status(200).json({
      success: true,
      count: files.length,
      data: { files }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Error fetching files',
      error: error.message
    });
  }
};

// @desc    Get file by ID
// @route   GET /api/files/:id
// @access  Private
const getFileById = async (req, res) => {
  try {
    const file = await File.findById(req.params.id)
      .populate('uploadedBy', 'username email');

    if (!file) {
      return res.status(404).json({
        success: false,
        message: 'File not found'
      });
    }

    // Check if user owns the file or is admin
    if (file.uploadedBy._id.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
      return res.status(403).json({
        success: false,
        message: 'Access denied'
      });
    }

    res.status(200).json({
      success: true,
      data: { file }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Error fetching file',
      error: error.message
    });
  }
};

// @desc    Download output file
// @route   GET /api/files/:id/download/:fileName
// @access  Private
const downloadOutputFile = async (req, res) => {
  try {
    const file = await File.findById(req.params.id);

    if (!file) {
      return res.status(404).json({
        success: false,
        message: 'File not found'
      });
    }

    // Check if user owns the file or is admin
    if (file.uploadedBy.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
      return res.status(403).json({
        success: false,
        message: 'Access denied'
      });
    }

    // Find the requested output file
    const outputFile = file.outputFiles.find(f => f.fileName === req.params.fileName);

    if (!outputFile) {
      return res.status(404).json({
        success: false,
        message: 'Output file not found'
      });
    }

    // Download from GridFS (all files are stored in GridFS)
    if (!outputFile.storedInGridFS || !outputFile.gridfsFileId) {
      return res.status(404).json({
        success: false,
        message: 'File not found in GridFS storage'
      });
    }

    // Download from GridFS
    const { downloadStream, fileName, contentType } = await downloadFromGridFS(outputFile.gridfsFileId);

    // Set headers
    res.set({
      'Content-Type': contentType,
      'Content-Disposition': `attachment; filename="${fileName}"`
    });

    // Pipe the GridFS stream to response
    downloadStream.pipe(res);

  } catch (error) {
    console.error('Error downloading file:', error);
    res.status(500).json({
      success: false,
      message: 'Error downloading file',
      error: error.message
    });
  }
};

// @desc    Delete file
// @route   DELETE /api/files/:id
// @access  Private
const deleteFile = async (req, res) => {
  try {
    const file = await File.findById(req.params.id);

    if (!file) {
      return res.status(404).json({
        success: false,
        message: 'File not found'
      });
    }

    // Check if user owns the file or is admin
    if (file.uploadedBy.toString() !== req.user._id.toString() && req.user.role !== 'admin') {
      return res.status(403).json({
        success: false,
        message: 'Access denied'
      });
    }

    // Delete input file from GridFS
    if (file.gridfsInputFileId) {
      try {
        await deleteFromGridFS(file.gridfsInputFileId);
        console.log(`Deleted input file from GridFS: ${file.originalName}`);
      } catch (error) {
        console.error(`Error deleting input file from GridFS:`, error);
        // Continue with other deletions even if one fails
      }
    }

    // Delete output files from GridFS
    if (file.outputFiles && file.outputFiles.length > 0) {
      for (const outputFile of file.outputFiles) {
        if (outputFile.storedInGridFS && outputFile.gridfsFileId) {
          try {
            await deleteFromGridFS(outputFile.gridfsFileId);
            console.log(`Deleted output file from GridFS: ${outputFile.fileName}`);
          } catch (error) {
            console.error(`Error deleting GridFS file ${outputFile.fileName}:`, error);
            // Continue with other deletions even if one fails
          }
        }
      }
    }

    // Clean up any legacy local files (for backward compatibility)
    if (file.filePath) {
      await cleanupFile(file.filePath);
    }
    if (file.outputPath) {
      await cleanupDirectory(file.outputPath);
    }

    await file.deleteOne();

    res.status(200).json({
      success: true,
      message: 'File deleted successfully'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      message: 'Error deleting file',
      error: error.message
    });
  }
};

module.exports = {
  uploadFile,
  getUserFiles,
  getAllFiles,
  getFileById,
  downloadOutputFile,
  deleteFile
};
