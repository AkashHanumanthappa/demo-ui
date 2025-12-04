import { createContext, useState, useEffect, useContext } from 'react';
import api from '../utils/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const initAuth = async () => {
      const token = localStorage.getItem('manuscript_token');

      if (token) {
        try {
          // Verify token and get user info
          const response = await api.get('/users/me');
          setUser(response.data.data.user);
        } catch (error) {
          console.error('Failed to verify token:', error);
          // Clear invalid token
          localStorage.removeItem('manuscript_token');
          localStorage.removeItem('manuscript_user');
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (credentials) => {
    try {
      const response = await api.post('/users/login', {
        email: credentials.email,
        password: credentials.password,
      });

      const { token, user: userData } = response.data.data;

      // Store token and user data
      localStorage.setItem('manuscript_token', token);
      localStorage.setItem('manuscript_user', JSON.stringify(userData));
      setUser(userData);

      return userData;
    } catch (error) {
      console.error('Login failed:', error);
      throw new Error(error.response?.data?.message || error.message || 'Login failed');
    }
  };

  const register = async (credentials) => {
    try {
      // Note: Registration requires admin privileges in the backend
      // For now, throw an error directing users to contact admin
      throw new Error('Please contact an administrator to create an account');
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    localStorage.removeItem('manuscript_token');
    localStorage.removeItem('manuscript_refresh_token');
    localStorage.removeItem('manuscript_user');
    setUser(null);
  };

  const getCurrentUserInfo = async () => {
    try {
      const response = await api.get('/users/me');
      const userData = response.data.data.user;
      setUser(userData);
      localStorage.setItem('manuscript_user', JSON.stringify(userData));
      return userData;
    } catch (error) {
      console.error('Failed to get user info:', error);
      throw error;
    }
  };

  const getCurrentUserProfile = async () => {
    return getCurrentUserInfo();
  };

  const updateProfile = async (profileData) => {
    try {
      if (!user) throw new Error('No user logged in');

      const response = await api.put(`/users/${user.id}`, profileData);
      const updatedUser = response.data.data.user;

      setUser(updatedUser);
      localStorage.setItem('manuscript_user', JSON.stringify(updatedUser));
      return updatedUser;
    } catch (error) {
      console.error('Failed to update profile:', error);
      throw new Error(error.response?.data?.message || error.message || 'Failed to update profile');
    }
  };

  const changePassword = async (passwordData) => {
    try {
      if (!user) throw new Error('No user logged in');

      const response = await api.put(`/users/${user.id}`, {
        password: passwordData.newPassword,
      });

      return { message: 'Password changed successfully' };
    } catch (error) {
      console.error('Failed to change password:', error);
      throw new Error(error.response?.data?.message || error.message || 'Failed to change password');
    }
  };

  const requestPasswordReset = async (email) => {
    // Backend doesn't have password reset endpoint yet
    throw new Error('Password reset not available. Please contact an administrator.');
  };

  const validateToken = async () => {
    try {
      const response = await api.get('/users/me');
      return response.data.data.user;
    } catch (error) {
      return null;
    }
  };

  const isAuthenticated = () => {
    return !!user;
  };

  const hasRole = (role) => {
    return user?.role === role;
  };

  const isAdmin = () => {
    return hasRole('admin') || hasRole('super_admin');
  };

  const getUserDisplayName = () => {
    if (!user) return '';

    // Backend user model has username, not first_name/last_name
    if (user.username) {
      return user.username;
    } else {
      return user.email;
    }
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    getCurrentUserInfo,
    getCurrentUserProfile,
    updateProfile,
    changePassword,
    requestPasswordReset,
    validateToken,
    isAuthenticated,
    hasRole,
    isAdmin,
    getUserDisplayName,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export { AuthContext };
