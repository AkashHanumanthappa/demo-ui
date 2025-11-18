const mongoose = require('mongoose');
const { GridFSBucket } = require('mongodb');
const File = require('../models/File');
const { deleteFromGridFS } = require('./gridfs');

/**
 * Storage Management Utility
 * Handles MongoDB storage quota monitoring and cleanup
 */

// Storage quota limits (in bytes)
const STORAGE_LIMITS = {
  MAX_STORAGE: 512 * 1024 * 1024, // 512 MB
  WARNING_THRESHOLD: 0.85, // 85% - start warning
  CLEANUP_THRESHOLD: 0.90, // 90% - start automatic cleanup
  CRITICAL_THRESHOLD: 0.95, // 95% - prevent new uploads
  TARGET_AFTER_CLEANUP: 0.70 // 70% - target usage after cleanup
};

/**
 * Get current GridFS storage usage
 * @returns {Promise<Object>} Storage statistics
 */
const getStorageStats = async () => {
  try {
    const db = mongoose.connection.db;
    const bucket = new GridFSBucket(db, { bucketName: 'outputFiles' });

    // Get all files from GridFS
    const files = await bucket.find({}).toArray();

    // Calculate total size
    let totalSize = 0;
    let fileCount = files.length;

    files.forEach(file => {
      totalSize += file.length || 0;
    });

    const usagePercent = (totalSize / STORAGE_LIMITS.MAX_STORAGE) * 100;

    return {
      totalSize,
      totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
      maxStorageMB: (STORAGE_LIMITS.MAX_STORAGE / (1024 * 1024)).toFixed(2),
      usagePercent: usagePercent.toFixed(2),
      fileCount,
      available: STORAGE_LIMITS.MAX_STORAGE - totalSize,
      availableMB: ((STORAGE_LIMITS.MAX_STORAGE - totalSize) / (1024 * 1024)).toFixed(2),
      status: getStorageStatus(usagePercent)
    };
  } catch (error) {
    console.error('Error getting storage stats:', error);
    throw error;
  }
};

/**
 * Determine storage status based on usage
 * @param {number} usagePercent
 * @returns {string}
 */
const getStorageStatus = (usagePercent) => {
  if (usagePercent >= STORAGE_LIMITS.CRITICAL_THRESHOLD * 100) {
    return 'critical';
  } else if (usagePercent >= STORAGE_LIMITS.CLEANUP_THRESHOLD * 100) {
    return 'high';
  } else if (usagePercent >= STORAGE_LIMITS.WARNING_THRESHOLD * 100) {
    return 'warning';
  }
  return 'normal';
};

/**
 * Check if there's enough space for an upload
 * @param {number} fileSize - Size of file to upload (in bytes)
 * @returns {Promise<Object>} Object with canUpload boolean and reason
 */
const checkStorageAvailability = async (fileSize) => {
  try {
    const stats = await getStorageStats();
    const usagePercent = parseFloat(stats.usagePercent);

    // Critical threshold - prevent uploads
    if (usagePercent >= STORAGE_LIMITS.CRITICAL_THRESHOLD * 100) {
      return {
        canUpload: false,
        reason: 'Storage quota critical. Please delete old files or contact administrator.',
        stats
      };
    }

    // Check if file would exceed quota
    const projectedSize = stats.totalSize + fileSize;
    const projectedPercent = (projectedSize / STORAGE_LIMITS.MAX_STORAGE) * 100;

    if (projectedPercent > 100) {
      return {
        canUpload: false,
        reason: 'File size exceeds available storage. Please delete old files first.',
        stats
      };
    }

    // High usage - trigger cleanup but allow upload
    if (usagePercent >= STORAGE_LIMITS.CLEANUP_THRESHOLD * 100) {
      return {
        canUpload: true,
        shouldCleanup: true,
        reason: 'Storage is high. Automatic cleanup recommended.',
        stats
      };
    }

    return {
      canUpload: true,
      shouldCleanup: false,
      stats
    };
  } catch (error) {
    console.error('Error checking storage availability:', error);
    // On error, allow upload but log warning
    return {
      canUpload: true,
      shouldCleanup: false,
      error: error.message
    };
  }
};

/**
 * Get files sorted by age (oldest first)
 * @param {number} limit - Maximum number of files to return
 * @returns {Promise<Array>} Array of file documents
 */
const getOldestFiles = async (limit = 50) => {
  try {
    const files = await File.find()
      .sort({ createdAt: 1 }) // Oldest first
      .limit(limit)
      .select('_id originalName createdAt fileSize gridfsInputFileId outputFiles uploadedBy status');

    return files;
  } catch (error) {
    console.error('Error getting oldest files:', error);
    throw error;
  }
};

/**
 * Get failed or orphaned files
 * @returns {Promise<Array>} Array of file documents
 */
const getCleanupCandidates = async () => {
  try {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const candidates = await File.find({
      $or: [
        { status: 'failed' }, // Failed uploads
        {
          status: 'uploaded',
          createdAt: { $lt: thirtyDaysAgo }
        }, // Old uploaded but not processed files
        {
          status: 'processing',
          processingStartedAt: { $lt: thirtyDaysAgo }
        } // Stuck processing files
      ]
    }).sort({ createdAt: 1 });

    return candidates;
  } catch (error) {
    console.error('Error getting cleanup candidates:', error);
    throw error;
  }
};

/**
 * Delete a file and all its GridFS data
 * @param {Object} file - File document
 * @returns {Promise<Object>} Deletion result
 */
const deleteFileCompletely = async (file) => {
  try {
    let deletedSize = 0;
    const deletedFiles = [];

    // Delete input file from GridFS
    if (file.gridfsInputFileId) {
      try {
        await deleteFromGridFS(file.gridfsInputFileId);
        deletedSize += file.fileSize || 0;
        deletedFiles.push({ type: 'input', name: file.originalName });
      } catch (error) {
        console.error(`Error deleting input file from GridFS:`, error);
      }
    }

    // Delete output files from GridFS
    if (file.outputFiles && file.outputFiles.length > 0) {
      for (const outputFile of file.outputFiles) {
        if (outputFile.storedInGridFS && outputFile.gridfsFileId) {
          try {
            await deleteFromGridFS(outputFile.gridfsFileId);
            deletedSize += outputFile.fileSize || 0;
            deletedFiles.push({ type: 'output', name: outputFile.fileName });
          } catch (error) {
            console.error(`Error deleting output file ${outputFile.fileName}:`, error);
          }
        }
      }
    }

    // Delete file document
    await file.deleteOne();

    return {
      fileId: file._id,
      fileName: file.originalName,
      deletedSize,
      deletedFiles,
      createdAt: file.createdAt
    };
  } catch (error) {
    console.error('Error deleting file completely:', error);
    throw error;
  }
};

/**
 * Perform automatic cleanup to reach target storage usage
 * @param {number} targetPercent - Target usage percentage (default 70%)
 * @returns {Promise<Object>} Cleanup result
 */
const performAutoCleanup = async (targetPercent = STORAGE_LIMITS.TARGET_AFTER_CLEANUP) => {
  try {
    console.log('Starting automatic storage cleanup...');

    const initialStats = await getStorageStats();
    const targetSize = STORAGE_LIMITS.MAX_STORAGE * targetPercent;
    const sizeToFree = initialStats.totalSize - targetSize;

    if (sizeToFree <= 0) {
      return {
        success: true,
        message: 'Storage already below target threshold',
        initialStats,
        finalStats: initialStats,
        deletedFiles: []
      };
    }

    console.log(`Need to free ${(sizeToFree / (1024 * 1024)).toFixed(2)} MB`);

    let freedSize = 0;
    const deletedFiles = [];

    // Phase 1: Delete failed and orphaned files
    const cleanupCandidates = await getCleanupCandidates();
    console.log(`Found ${cleanupCandidates.length} cleanup candidates`);

    for (const file of cleanupCandidates) {
      if (freedSize >= sizeToFree) break;

      try {
        const result = await deleteFileCompletely(file);
        freedSize += result.deletedSize;
        deletedFiles.push(result);
        console.log(`Deleted: ${result.fileName} (${(result.deletedSize / 1024).toFixed(2)} KB)`);
      } catch (error) {
        console.error(`Error deleting file ${file._id}:`, error);
      }
    }

    // Phase 2: If still need more space, delete oldest completed files
    if (freedSize < sizeToFree) {
      console.log('Phase 2: Deleting oldest completed files...');

      const oldFiles = await File.find({ status: 'completed' })
        .sort({ createdAt: 1 })
        .limit(100);

      for (const file of oldFiles) {
        if (freedSize >= sizeToFree) break;

        try {
          const result = await deleteFileCompletely(file);
          freedSize += result.deletedSize;
          deletedFiles.push(result);
          console.log(`Deleted: ${result.fileName} (${(result.deletedSize / 1024).toFixed(2)} KB)`);
        } catch (error) {
          console.error(`Error deleting file ${file._id}:`, error);
        }
      }
    }

    const finalStats = await getStorageStats();

    console.log(`Cleanup completed. Freed ${(freedSize / (1024 * 1024)).toFixed(2)} MB`);

    return {
      success: true,
      message: `Cleanup completed. Deleted ${deletedFiles.length} files.`,
      initialStats,
      finalStats,
      deletedFiles,
      freedSize,
      freedSizeMB: (freedSize / (1024 * 1024)).toFixed(2)
    };
  } catch (error) {
    console.error('Error performing auto cleanup:', error);
    throw error;
  }
};

/**
 * Clean up orphaned GridFS files (files not referenced in File collection)
 * @returns {Promise<Object>} Cleanup result
 */
const cleanupOrphanedGridFSFiles = async () => {
  try {
    const db = mongoose.connection.db;
    const bucket = new GridFSBucket(db, { bucketName: 'outputFiles' });

    // Get all GridFS files
    const gridfsFiles = await bucket.find({}).toArray();

    // Get all file references from File collection
    const dbFiles = await File.find({}).select('gridfsInputFileId outputFiles');

    const referencedIds = new Set();

    // Collect all referenced GridFS IDs
    dbFiles.forEach(file => {
      if (file.gridfsInputFileId) {
        referencedIds.add(file.gridfsInputFileId.toString());
      }
      if (file.outputFiles) {
        file.outputFiles.forEach(output => {
          if (output.gridfsFileId) {
            referencedIds.add(output.gridfsFileId.toString());
          }
        });
      }
    });

    // Find orphaned files
    const orphanedFiles = gridfsFiles.filter(
      gFile => !referencedIds.has(gFile._id.toString())
    );

    console.log(`Found ${orphanedFiles.length} orphaned GridFS files`);

    let deletedCount = 0;
    let freedSize = 0;

    for (const orphan of orphanedFiles) {
      try {
        await deleteFromGridFS(orphan._id);
        deletedCount++;
        freedSize += orphan.length;
        console.log(`Deleted orphaned file: ${orphan.filename} (${(orphan.length / 1024).toFixed(2)} KB)`);
      } catch (error) {
        console.error(`Error deleting orphaned file ${orphan._id}:`, error);
      }
    }

    return {
      success: true,
      message: `Cleaned up ${deletedCount} orphaned GridFS files`,
      deletedCount,
      freedSize,
      freedSizeMB: (freedSize / (1024 * 1024)).toFixed(2)
    };
  } catch (error) {
    console.error('Error cleaning up orphaned GridFS files:', error);
    throw error;
  }
};

module.exports = {
  getStorageStats,
  checkStorageAvailability,
  getOldestFiles,
  getCleanupCandidates,
  deleteFileCompletely,
  performAutoCleanup,
  cleanupOrphanedGridFSFiles,
  STORAGE_LIMITS
};
