const express = require('express');
const router = express.Router();
const {
  uploadFile,
  getUserFiles,
  getAllFiles,
  getFileById,
  downloadOutputFile,
  deleteFile,
  getConversionDashboardFiles
} = require('../controllers/fileController');
const { authenticate, authorizeAdmin } = require('../middleware/auth');
const { upload, handleMulterError } = require('../middleware/upload');

// All routes require authentication
router.use(authenticate);

// File upload route
router.post('/upload', upload.single('file'), handleMulterError, uploadFile);

// Get user's files
router.get('/', getUserFiles);


router.get('/conversion-dashboard', authorizeAdmin, getConversionDashboardFiles);


// Get all files (Admin only)
router.get('/all', authorizeAdmin, getAllFiles);

// Get file by ID
router.get('/:id', getFileById);

// Download output file
router.get('/:id/download/:fileName', downloadOutputFile);

// Delete file
router.delete('/:id', deleteFile);

module.exports = router;
