const File = require('../models/File');
const path = require('path');
const { executeConverter, cleanupFile } = require('../utils/docConverter');

// @desc    Upload and process file
// @route   POST /api/files/upload
// @access  Private
const uploadFile = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, message: 'No file uploaded' });
    }

    const { originalname, filename, path: filePath, size, mimetype } = req.file;
    const fileType = path.extname(originalname).toLowerCase().replace('.', '');

    // Save file record in DB
    const file = await File.create({
      originalName: originalname,
      fileName: filename,
      filePath: filePath,
      fileType: fileType,
      fileSize: size,
      mimeType: mimetype,
      uploadedBy: req.user._id,
      status: 'uploaded'
    });
      processFileAsync(file);
    // Run converter and **wait** for it to finish
    try {
      const outputDir = path.join(__dirname, '../outputs', file._id.toString());
      const conversionResult = await executeConverter(filePath, outputDir);

      // Save output files to DB
      file.outputFiles = conversionResult.outputFiles;
      await file.save();

      res.status(200).json({
        success: true,
        message: 'File uploaded and converted successfully',
        data: { file }
      });
    } catch (conversionError) {
      console.error('File processing failed:', conversionError);

      res.status(500).json({
        success: false,
        message: 'File processing failed',
        error: conversionError.message || conversionError
      });
    }
  } catch (error) {
    if (req.file) {
      await cleanupFile(req.file.path);
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
  try {
    // Validate file object
    if (!file || !file._id || !file.filePath) {
      console.error('Invalid file object passed to processFileAsync:', file);
      throw new Error('Invalid file object');
    }

    // Update status to processing
    await file.updateStatus('processing');

    // Create output directory for this file
    const outputDir = path.join(__dirname, '../outputs', file._id.toString());

    console.log(`Processing file ${file._id}: ${file.originalName}`);

    // Execute converter
    const result = await executeConverter(file.filePath, outputDir);

    // Update file record with results
    await file.updateStatus('completed', {
      outputPath: result.outputPath,
      outputFiles: result.outputFiles,
      conversionMetadata: {
        conversionType: 'RittDocConverter',
        outputFormats: result.outputFiles.map(f => f.fileType)
      }
    });

    console.log(`File ${file._id} processed successfully`);

  } catch (error) {
    console.error(`File processing failed:`, error);

    // Try to update status to failed if file object is valid
    if (file && file.updateStatus) {
      try {
        await file.updateStatus('failed', {
          errorMessage: error.message || error.error || 'Conversion failed'
        });
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

    // Send file
    res.download(outputFile.filePath, outputFile.fileName);

  } catch (error) {
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

    // Clean up files
    await cleanupFile(file.filePath);
    if (file.outputPath) {
      const { cleanupDirectory } = require('../utils/docConverter');
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
