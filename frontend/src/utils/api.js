// API utility with Axios and authentication
import axios from 'axios';
import environment from '../config/environment';

// Create axios instance
const api = axios.create({
  baseURL: environment.apiUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Request interceptor - Add auth token to all requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('manuscript_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors globally
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle authentication errors
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('manuscript_token');
      localStorage.removeItem('manuscript_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    // Enhance error message
    const errorMessage = error.response?.data?.message ||
                         error.response?.data?.error ||
                         error.message ||
                         'An unexpected error occurred';

    error.message = errorMessage;
    return Promise.reject(error);
  }
);

// ============================================
// AUTH / USER ENDPOINTS
// ============================================

/**
 * Login user
 * @param {Object} credentials - { email, password }
 * @returns {Promise} - { token, user }
 */
export const login = async (credentials) => {
  const response = await api.post('/users/login', credentials);
  if (response.data.success && response.data.data.token) {
    // Store token and user info
    localStorage.setItem('manuscript_token', response.data.data.token);
    localStorage.setItem('manuscript_user', JSON.stringify(response.data.data.user));
  }
  return response.data;
};

/**
 * Logout user (client-side only)
 */
export const logout = () => {
  localStorage.removeItem('manuscript_token');
  localStorage.removeItem('manuscript_user');
  window.location.href = '/login';
};

/**
 * Get current user profile
 * @returns {Promise} - { user }
 */
export const getCurrentUser = async () => {
  const response = await api.get('/users/me');
  return response.data;
};

/**
 * Create new user (Admin only)
 * @param {Object} userData - { username, email, password, role }
 * @returns {Promise} - { user }
 */
export const createUser = async (userData) => {
  const response = await api.post('/users', userData);
  return response.data;
};

/**
 * Get all users (Admin only)
 * @returns {Promise} - { users, count }
 */
export const getAllUsers = async () => {
  const response = await api.get('/users');
  return response.data;
};

/**
 * Update user (Admin only)
 * @param {String} userId - User ID
 * @param {Object} userData - { username, email, role }
 * @returns {Promise} - { user }
 */
export const updateUser = async (userId, userData) => {
  const response = await api.put(`/users/${userId}`, userData);
  return response.data;
};

/**
 * Delete user (Admin only)
 * @param {String} userId - User ID
 * @returns {Promise} - { message }
 */
export const deleteUser = async (userId) => {
  const response = await api.delete(`/users/${userId}`);
  return response.data;
};

// ============================================
// FILE / MANUSCRIPT ENDPOINTS
// ============================================

/**
 * Upload file for processing
 * @param {File} file - File object from input
 * @param {Function} onUploadProgress - Progress callback (optional)
 * @returns {Promise} - { file }
 */
export const uploadFile = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5 minutes for large file uploads
    onUploadProgress: (progressEvent) => {
      if (onUploadProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onUploadProgress({
          progress: percentCompleted,
          loaded: progressEvent.loaded,
          total: progressEvent.total
        });
      }
    },
  });

  return response.data;
};

/**
 * Get all files for current user
 * @param {Object} params - Query parameters (optional)
 * @returns {Promise} - { files, count }
 */
export const getUserFiles = async (params = {}) => {
  const response = await api.get('/files', { params });
  return response.data;
};

/**
 * Get all files (Admin only)
 * @param {Object} params - Query parameters (optional)
 * @returns {Promise} - { files, count }
 */
export const getAllFiles = async (params = {}) => {
  const response = await api.get('/files/all', { params });
  return response.data;
};

/**
 * Get file by ID
 * @param {String} fileId - File ID
 * @returns {Promise} - { file }
 */
export const getFileById = async (fileId) => {
  const response = await api.get(`/files/${fileId}`);
  return response.data;
};

/**
 * Get download URL for output file
 * @param {String} fileId - File ID
 * @param {String} fileName - Output file name
 * @returns {String} - Download URL
 */
export const getDownloadUrl = (fileId, fileName) => {
  const token = localStorage.getItem('manuscript_token');
  return `${environment.apiUrl}/files/${fileId}/download/${encodeURIComponent(fileName)}?token=${token}`;
};

/**
 * Download output file
 * @param {String} fileId - File ID
 * @param {String} fileName - Output file name
 * @returns {Promise} - Blob
 */
export const downloadFile = async (fileId, fileName) => {
  const response = await api.get(`/files/${fileId}/download/${encodeURIComponent(fileName)}`, {
    responseType: 'blob',
    timeout: 60000, // 1 minute for downloads
  });
  return response.data;
};

/**
 * Delete file
 * @param {String} fileId - File ID
 * @returns {Promise} - { message }
 */
export const deleteFile = async (fileId) => {
  const response = await api.delete(`/files/${fileId}`);
  return response.data;
};

// ============================================
// HEALTH CHECK
// ============================================

/**
 * Check server health
 * @returns {Promise} - { message, timestamp }
 */
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Check if user is authenticated
 * @returns {Boolean}
 */
export const isAuthenticated = () => {
  return !!localStorage.getItem('manuscript_token');
};

/**
 * Get stored user info
 * @returns {Object|null}
 */
export const getStoredUser = () => {
  const userStr = localStorage.getItem('manuscript_user');
  return userStr ? JSON.parse(userStr) : null;
};

/**
 * Check if user is admin
 * @returns {Boolean}
 */
export const isAdmin = () => {
  const user = getStoredUser();
  return user?.role === 'admin';
};

/**
 * Format file size
 * @param {Number} bytes - File size in bytes
 * @returns {String} - Formatted size
 */
export const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Format date
 * @param {String|Date} date - Date to format
 * @returns {String} - Formatted date
 */
export const formatDate = (date) => {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Get file status info
 * @param {String} status - File status
 * @returns {Object} - { label, color, description }
 */
export const getFileStatusInfo = (status) => {
  const statusMap = {
    uploaded: {
      label: 'Uploaded',
      color: 'yellow',
      description: 'File uploaded to server'
    },
    processing: {
      label: 'Processing',
      color: 'blue',
      description: 'Converting file formats'
    },
    completed: {
      label: 'Completed',
      color: 'green',
      description: 'Ready for download'
    },
    failed: {
      label: 'Failed',
      color: 'red',
      description: 'Conversion failed'
    }
  };
  return statusMap[status] || statusMap.uploaded;
};

/**
 * Change current user's password
 * @param {String} currentPassword - Current password
 * @param {String} newPassword - New password
 * @returns {Promise} - { message }
 */
export const changePassword = async (currentPassword, newPassword) => {
  const response = await api.patch('/users/me/password', {
    currentPassword,
    newPassword
  });
  return response.data;
};


// Export axios instance as default for custom requests
export default api;