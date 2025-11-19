const express = require('express');
const router = express.Router();
const {
  createUser,
  loginUser,
  getAllUsers,
  getCurrentUser,
  updateUser,
  deleteUser,
  changePassword
} = require('../controllers/userController');
const { authenticate, authorizeAdmin } = require('../middleware/auth');

// Public routes
router.post('/login', loginUser);

// Protected routes (require authentication)
router.get('/me', authenticate, getCurrentUser);
router.patch('/me/password', authenticate, changePassword);
// Admin only routes
router.post('/', authenticate, authorizeAdmin, createUser);
router.get('/', authenticate, authorizeAdmin, getAllUsers);
router.put('/:id', authenticate, authorizeAdmin, updateUser);
router.delete('/:id', authenticate, authorizeAdmin, deleteUser);

module.exports = router;
