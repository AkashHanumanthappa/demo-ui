const mongoose = require('mongoose');
const { GridFSBucket } = require('mongodb');
const fs = require('fs');
const path = require('path');

let gridfsBucket;

/**
 * Initialize GridFS bucket
 */
const initGridFS = () => {
  if (!gridfsBucket) {
    const db = mongoose.connection.db;
    gridfsBucket = new GridFSBucket(db, {
      bucketName: 'outputFiles'
    });
    console.log('GridFS initialized');
  }
  return gridfsBucket;
};

/**
 * Upload a file to GridFS from multer file object
 * @param {Object} file - Multer file object
 * @param {Object} metadata - Additional metadata to store
 * @returns {Promise<Object>} - Object containing fileId and file info
 */
const uploadFileToGridFS = async (file, metadata = {}) => {
  return new Promise((resolve, reject) => {
    const bucket = initGridFS();

    // Create upload stream
    const uploadStream = bucket.openUploadStream(file.originalname, {
      metadata: {
        ...metadata,
        uploadedAt: new Date(),
        originalName: file.originalname,
        mimeType: file.mimetype
      }
    });

    // Create read stream from file path and pipe to GridFS
    const readStream = fs.createReadStream(file.path);

    readStream.pipe(uploadStream)
      .on('error', (error) => {
        console.error('Error uploading to GridFS:', error);
        reject(error);
      })
      .on('finish', () => {
        resolve({
          fileId: uploadStream.id,
          fileName: file.originalname,
          fileSize: file.size,
          fileType: path.extname(file.originalname).toLowerCase().replace('.', ''),
          uploadedAt: new Date()
        });
      });
  });
};

/**
 * Upload a file to GridFS
 * @param {string} filePath - Path to the file on disk
 * @param {string} fileName - Name to store the file as
 * @param {Object} metadata - Additional metadata to store
 * @returns {Promise<Object>} - Object containing fileId and file info
 */
const uploadToGridFS = async (filePath, fileName, metadata = {}) => {
  return new Promise((resolve, reject) => {
    const bucket = initGridFS();

    // Get file stats
    const stats = fs.statSync(filePath);

    // Create upload stream
    const uploadStream = bucket.openUploadStream(fileName, {
      metadata: {
        ...metadata,
        uploadedAt: new Date(),
        originalPath: filePath
      }
    });

    // Create read stream and pipe to GridFS
    const readStream = fs.createReadStream(filePath);

    readStream.pipe(uploadStream)
      .on('error', (error) => {
        console.error('Error uploading to GridFS:', error);
        reject(error);
      })
      .on('finish', () => {
        resolve({
          fileId: uploadStream.id,
          fileName: fileName,
          fileSize: stats.size,
          fileType: path.extname(fileName).toLowerCase().replace('.', ''),
          uploadedAt: new Date()
        });
      });
  });
};

/**
 * Download a file from GridFS
 * @param {ObjectId} fileId - GridFS file ID
 * @returns {Promise<Object>} - Object with downloadStream and file info
 */
const downloadFromGridFS = async (fileId) => {
  return new Promise(async (resolve, reject) => {
    try {
      const bucket = initGridFS();

      // Convert string to ObjectId if needed
      const objectId = typeof fileId === 'string' ? new mongoose.Types.ObjectId(fileId) : fileId;

      // Get file info
      const files = await bucket.find({ _id: objectId }).toArray();

      if (!files || files.length === 0) {
        return reject(new Error('File not found in GridFS'));
      }

      const file = files[0];

      // Validate file size
      if (!file.length || file.length === 0) {
        return reject(new Error('File is empty or corrupted'));
      }

      // Create download stream
      const downloadStream = bucket.openDownloadStream(objectId);

      // Add error handler to catch stream initialization errors
      downloadStream.on('error', (error) => {
        console.error('GridFS download stream error:', error);
        reject(error);
      });

      resolve({
        downloadStream,
        fileName: file.filename,
        fileSize: file.length,
        contentType: getContentType(file.filename),
        metadata: file.metadata
      });
    } catch (error) {
      console.error('Error downloading from GridFS:', error);
      reject(error);
    }
  });
};

/**
 * Delete a file from GridFS
 * @param {ObjectId} fileId - GridFS file ID
 * @returns {Promise<void>}
 */
const deleteFromGridFS = async (fileId) => {
  try {
    const bucket = initGridFS();

    // Convert string to ObjectId if needed
    const objectId = typeof fileId === 'string' ? new mongoose.Types.ObjectId(fileId) : fileId;

    await bucket.delete(objectId);
    console.log('Deleted file from GridFS:', fileId);
  } catch (error) {
    console.error('Error deleting from GridFS:', error);
    throw error;
  }
};

/**
 * Upload multiple files to GridFS
 * @param {Array<Object>} files - Array of file objects with filePath and fileName
 * @param {Object} metadata - Common metadata for all files
 * @returns {Promise<Array>} - Array of uploaded file info
 */
const uploadMultipleToGridFS = async (files, metadata = {}) => {
  const uploadPromises = files.map(file =>
    uploadToGridFS(file.filePath, file.fileName, {
      ...metadata,
      originalFileType: file.fileType
    })
  );

  return Promise.all(uploadPromises);
};

/**
 * Get content type based on file extension
 * @param {string} fileName
 * @returns {string}
 */
const getContentType = (fileName) => {
  const ext = path.extname(fileName).toLowerCase();
  const contentTypes = {
    '.pdf': 'application/pdf',
    '.epub': 'application/epub+zip',
    '.txt': 'text/plain',
    '.html': 'text/html',
    '.json': 'application/json',
    '.xml': 'application/xml',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif'
  };

  return contentTypes[ext] || 'application/octet-stream';
};

/**
 * Check if a file exists in GridFS
 * @param {ObjectId} fileId - GridFS file ID
 * @returns {Promise<boolean>}
 */
const fileExistsInGridFS = async (fileId) => {
  try {
    const bucket = initGridFS();
    const objectId = typeof fileId === 'string' ? new mongoose.Types.ObjectId(fileId) : fileId;
    const files = await bucket.find({ _id: objectId }).toArray();
    return files && files.length > 0;
  } catch (error) {
    console.error('Error checking file existence in GridFS:', error);
    return false;
  }
};

/**
 * Download a file from GridFS to local path (for processing)
 * @param {ObjectId} fileId - GridFS file ID
 * @param {string} destinationPath - Local path to save the file
 * @returns {Promise<Object>} - Object with file info
 */
const downloadToLocal = async (fileId, destinationPath) => {
  return new Promise(async (resolve, reject) => {
    try {
      const bucket = initGridFS();

      // Convert string to ObjectId if needed
      const objectId = typeof fileId === 'string' ? new mongoose.Types.ObjectId(fileId) : fileId;

      // Get file info
      const files = await bucket.find({ _id: objectId }).toArray();

      if (!files || files.length === 0) {
        return reject(new Error('File not found in GridFS'));
      }

      const file = files[0];

      // Create download stream
      const downloadStream = bucket.openDownloadStream(objectId);
      const writeStream = fs.createWriteStream(destinationPath);

      downloadStream.pipe(writeStream)
        .on('error', (error) => {
          console.error('Error downloading from GridFS to local:', error);
          reject(error);
        })
        .on('finish', () => {
          resolve({
            fileName: file.filename,
            fileSize: file.length,
            filePath: destinationPath,
            metadata: file.metadata
          });
        });
    } catch (error) {
      console.error('Error downloading from GridFS to local:', error);
      reject(error);
    }
  });
};

module.exports = {
  initGridFS,
  uploadFileToGridFS,
  uploadToGridFS,
  downloadFromGridFS,
  downloadToLocal,
  deleteFromGridFS,
  uploadMultipleToGridFS,
  fileExistsInGridFS,
  getContentType
};
