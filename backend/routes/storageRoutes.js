const express = require('express');
const router = express.Router();
const {
  getStats,
  cleanup,
  cleanupOrphaned,
  getCleanupCandidatesList,
  getOldestFilesList,
  deleteMultipleFiles,
  getStorageReport
} = require('../controllers/storageController');
const { authenticate, authorizeAdmin } = require('../middleware/auth');

// All routes require authentication and admin role
router.use(authenticate);
router.use(authorizeAdmin);

// Get storage statistics
router.get('/stats', getStats);

// Get storage report
router.get('/report', getStorageReport);

// Get cleanup candidates
router.get('/cleanup-candidates', getCleanupCandidatesList);

// Get oldest files
router.get('/oldest-files', getOldestFilesList);

// Perform automatic cleanup
router.post('/cleanup', cleanup);

// Clean up orphaned GridFS files
router.post('/cleanup-orphaned', cleanupOrphaned);

// Delete multiple files
router.delete('/files', deleteMultipleFiles);

module.exports = router;
