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

export default api;
