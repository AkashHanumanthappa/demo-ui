const {
  getStorageStats,
  performAutoCleanup,
  cleanupOrphanedGridFSFiles,
  getCleanupCandidates,
  getOldestFiles,
  deleteFileCompletely
} = require('../utils/storageManager');
const File = require('../models/File');

// @desc    Get storage statistics
// @route   GET /api/storage/stats
// @access  Private/Admin
const getStats = async (req, res) => {
  try {
    const stats = await getStorageStats();

    res.status(200).json({
      success: true,
      data: { stats }
    });
  } catch (error) {
    console.error('Error getting storage stats:', error);
    res.status(500).json({
      success: false,
      message: 'Error fetching storage statistics',
      error: error.message
    });
  }
};

// @desc    Perform automatic cleanup
// @route   POST /api/storage/cleanup
// @access  Private/Admin
const cleanup = async (req, res) => {
  try {
    const { targetPercent } = req.body;

    const result = await performAutoCleanup(targetPercent);

    res.status(200).json({
      success: true,
      message: result.message,
      data: result
    });
  } catch (error) {
    console.error('Error performing cleanup:', error);
    res.status(500).json({
      success: false,
      message: 'Error performing cleanup',
      error: error.message
    });
  }
};

// @desc    Clean up orphaned GridFS files
// @route   POST /api/storage/cleanup-orphaned
// @access  Private/Admin
const cleanupOrphaned = async (req, res) => {
  try {
    const result = await cleanupOrphanedGridFSFiles();

    res.status(200).json({
      success: true,
      message: result.message,
      data: result
    });
  } catch (error) {
    console.error('Error cleaning orphaned files:', error);
    res.status(500).json({
      success: false,
      message: 'Error cleaning orphaned files',
      error: error.message
    });
  }
};

// @desc    Get cleanup candidates
// @route   GET /api/storage/cleanup-candidates
// @access  Private/Admin
const getCleanupCandidatesList = async (req, res) => {
  try {
    const candidates = await getCleanupCandidates();

    const candidatesWithSize = candidates.map(file => ({
      _id: file._id,
      originalName: file.originalName,
      status: file.status,
      createdAt: file.createdAt,
      fileSize: file.fileSize,
      outputFilesCount: file.outputFiles ? file.outputFiles.length : 0,
      totalSize: file.fileSize + (file.outputFiles || []).reduce((sum, f) => sum + (f.fileSize || 0), 0),
      uploadedBy: file.uploadedBy
    }));

    res.status(200).json({
      success: true,
      count: candidatesWithSize.length,
      data: { candidates: candidatesWithSize }
    });
  } catch (error) {
    console.error('Error getting cleanup candidates:', error);
    res.status(500).json({
      success: false,
      message: 'Error fetching cleanup candidates',
      error: error.message
    });
  }
};

// @desc    Get oldest files
// @route   GET /api/storage/oldest-files
// @access  Private/Admin
const getOldestFilesList = async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    const files = await getOldestFiles(limit);

    const filesWithSize = files.map(file => ({
      _id: file._id,
      originalName: file.originalName,
      status: file.status,
      createdAt: file.createdAt,
      fileSize: file.fileSize,
      outputFilesCount: file.outputFiles ? file.outputFiles.length : 0,
      totalSize: file.fileSize + (file.outputFiles || []).reduce((sum, f) => sum + (f.fileSize || 0), 0),
      uploadedBy: file.uploadedBy
    }));

    res.status(200).json({
      success: true,
      count: filesWithSize.length,
      data: { files: filesWithSize }
    });
  } catch (error) {
    console.error('Error getting oldest files:', error);
    res.status(500).json({
      success: false,
      message: 'Error fetching oldest files',
      error: error.message
    });
  }
};

// @desc    Delete specific files by IDs
// @route   DELETE /api/storage/files
// @access  Private/Admin
const deleteMultipleFiles = async (req, res) => {
  try {
    const { fileIds } = req.body;

    if (!fileIds || !Array.isArray(fileIds) || fileIds.length === 0) {
      return res.status(400).json({
        success: false,
        message: 'Please provide an array of file IDs to delete'
      });
    }

    const deletedFiles = [];
    const errors = [];
    let totalFreedSize = 0;

    for (const fileId of fileIds) {
      try {
        const file = await File.findById(fileId);

        if (!file) {
          errors.push({ fileId, error: 'File not found' });
          continue;
        }

        const result = await deleteFileCompletely(file);
        deletedFiles.push(result);
        totalFreedSize += result.deletedSize;
      } catch (error) {
        errors.push({ fileId, error: error.message });
      }
    }

    const stats = await getStorageStats();

    res.status(200).json({
      success: true,
      message: `Deleted ${deletedFiles.length} files`,
      data: {
        deletedFiles,
        errors,
        totalFreedSize,
        totalFreedSizeMB: (totalFreedSize / (1024 * 1024)).toFixed(2),
        currentStats: stats
      }
    });
  } catch (error) {
    console.error('Error deleting files:', error);
    res.status(500).json({
      success: false,
      message: 'Error deleting files',
      error: error.message
    });
  }
};

// @desc    Get storage report
// @route   GET /api/storage/report
// @access  Private/Admin
const getStorageReport = async (req, res) => {
  try {
    const stats = await getStorageStats();
    const cleanupCandidates = await getCleanupCandidates();

    // Get file count by status
    const statusCounts = await File.aggregate([
      {
        $group: {
          _id: '$status',
          count: { $sum: 1 },
          totalSize: { $sum: '$fileSize' }
        }
      }
    ]);

    // Get file count by user
    const userCounts = await File.aggregate([
      {
        $group: {
          _id: '$uploadedBy',
          count: { $sum: 1 },
          totalSize: { $sum: '$fileSize' }
        }
      },
      {
        $sort: { totalSize: -1 }
      },
      {
        $limit: 10
      }
    ]);

    // Get file count by type
    const typeCounts = await File.aggregate([
      {
        $group: {
          _id: '$fileType',
          count: { $sum: 1 },
          totalSize: { $sum: '$fileSize' }
        }
      }
    ]);

    res.status(200).json({
      success: true,
      data: {
        stats,
        cleanupCandidatesCount: cleanupCandidates.length,
        statusCounts,
        userCounts,
        typeCounts
      }
    });
  } catch (error) {
    console.error('Error generating storage report:', error);
    res.status(500).json({
      success: false,
      message: 'Error generating storage report',
      error: error.message
    });
  }
};

module.exports = {
  getStats,
  cleanup,
  cleanupOrphaned,
  getCleanupCandidatesList,
  getOldestFilesList,
  deleteMultipleFiles,
  getStorageReport
};
