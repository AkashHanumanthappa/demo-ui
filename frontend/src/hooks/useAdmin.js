import { useState, useCallback } from 'react';
import api from '../utils/api';

export const useAdmin = () => {
  const [users, setUsers] = useState([]);
  const [activityLogs, setActivityLogs] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);

  const getUsers = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      const response = await api.get('/users', { params });

      // Transform backend data to match frontend format
      const transformedUsers = response.data.users?.map(user => ({
        id: user._id,
        email: user.email,
        username: user.username,
        role: user.role,
        created_at: user.createdAt,
        updated_at: user.updatedAt,
      })) || [];

      setUsers(transformedUsers);
      return {
        users: transformedUsers,
        total: transformedUsers.length,
      };
    } catch (error) {
      console.error('Failed to fetch users:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateUser = useCallback(async (userId, userData) => {
    try {
      const response = await api.put(`/users/${userId}`, userData);
      const updatedUser = response.data.user;

      // Transform and update local state
      const transformedUser = {
        id: updatedUser._id,
        email: updatedUser.email,
        username: updatedUser.username,
        role: updatedUser.role,
        created_at: updatedUser.createdAt,
        updated_at: updatedUser.updatedAt,
      };

      setUsers((prev) =>
        prev.map((user) => (user.id === userId ? transformedUser : user))
      );

      return { message: 'User updated successfully' };
    } catch (error) {
      console.error('Failed to update user:', error);
      throw new Error(error.response?.data?.message || error.message || 'Failed to update user');
    }
  }, []);

  const deleteUser = useCallback(async (userId) => {
    try {
      await api.delete(`/users/${userId}`);
      setUsers((prev) => prev.filter((user) => user.id !== userId));
    } catch (error) {
      console.error('Failed to delete user:', error);
      throw new Error(error.response?.data?.message || error.message || 'Failed to delete user');
    }
  }, []);

  const bulkUpdateUsers = useCallback(async (userIds, updateData) => {
    try {
      // Since backend doesn't have bulk update, update one by one
      const promises = userIds.map(userId => api.put(`/users/${userId}`, updateData));
      await Promise.all(promises);

      // Refresh users list
      await getUsers();

      return { message: `${userIds.length} users updated successfully` };
    } catch (error) {
      console.error('Failed to bulk update users:', error);
      throw new Error(error.response?.data?.message || error.message || 'Failed to bulk update users');
    }
  }, []);

  const bulkDeleteUsers = useCallback(async (userIds) => {
    try {
      // Since backend doesn't have bulk delete, delete one by one
      const promises = userIds.map(userId => api.delete(`/users/${userId}`));
      await Promise.all(promises);

      setUsers((prev) => prev.filter((user) => !userIds.includes(user.id)));
    } catch (error) {
      console.error('Failed to bulk delete users:', error);
      throw new Error(error.response?.data?.message || error.message || 'Failed to bulk delete users');
    }
  }, []);

  const getUserStatistics = useCallback(async () => {
    try {
      // Get statistics based on current users data
      const adminUsers = users.filter(u => u.role === 'admin');
      const regularUsers = users.filter(u => u.role === 'user');

      return {
        total_users: users.length,
        admin_users: adminUsers.length,
        regular_users: regularUsers.length,
      };
    } catch (error) {
      console.error('Failed to get user statistics:', error);
      throw error;
    }
  }, [users]);

  const getActivityLogs = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      // Backend doesn't have activity logs endpoint yet
      // Return empty array for now
      setActivityLogs([]);
      return {
        activities: [],
        total: 0,
      };
    } catch (error) {
      console.error('Failed to fetch activity logs:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const getSystemHealth = useCallback(async () => {
    try {
      const response = await api.get('/health');
      return {
        status: response.data.success ? 'healthy' : 'unhealthy',
        timestamp: response.data.timestamp,
        database_status: 'connected',
      };
    } catch (error) {
      console.error('Failed to get system health:', error);
      return {
        status: 'unhealthy',
        database_status: 'disconnected',
      };
    }
  }, []);

  const getManuscriptReports = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      const response = await api.get('/files/all', { params });

      // Transform backend data to match frontend format
      const transformedReports = response.data.files?.map(file => ({
        id: file._id,
        manuscript_id: file._id,
        file_name: file.originalName,
        user_email: file.uploadedBy?.email || 'Unknown',
        status: file.status,
        created_at: file.createdAt,
        completed_at: file.processingCompletedAt,
        conversion_time: file.conversionMetadata?.processingTime,
        file_size: file.fileSize,
        error_message: file.errorMessage,
      })) || [];

      setReports(transformedReports);
      return {
        reports: transformedReports,
        total: response.data.count || transformedReports.length,
      };
    } catch (error) {
      console.error('Failed to fetch manuscript reports:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const retryConversion = useCallback(async (manuscriptId) => {
    try {
      // Backend doesn't have retry conversion endpoint yet
      // This would need to be implemented in the backend
      throw new Error('Retry conversion not yet implemented');
    } catch (error) {
      console.error('Failed to retry conversion:', error);
      throw error;
    }
  }, []);

  const getConversionStatistics = useCallback(async () => {
    try {
      // Calculate statistics from reports
      const totalConversions = reports.length;
      const successfulConversions = reports.filter(r => r.status === 'completed').length;
      const failedConversions = reports.filter(r => r.status === 'failed').length;
      const processingConversions = reports.filter(r => r.status === 'processing').length;

      const completedReports = reports.filter(r => r.status === 'completed' && r.conversion_time);
      const totalConversionTime = completedReports.reduce((sum, r) => sum + (r.conversion_time || 0), 0);
      const avgConversionTime = completedReports.length > 0 ? totalConversionTime / completedReports.length : 0;

      const totalSizeProcessed = reports.reduce((sum, r) => sum + (r.file_size || 0), 0);
      const successRate = totalConversions > 0 ? (successfulConversions / totalConversions) * 100 : 0;

      return {
        total_conversions: totalConversions,
        successful_conversions: successfulConversions,
        failed_conversions: failedConversions,
        processing_conversions: processingConversions,
        success_rate: successRate,
        average_conversion_time: avgConversionTime,
        total_size_processed: totalSizeProcessed,
      };
    } catch (error) {
      console.error('Failed to get conversion statistics:', error);
      throw error;
    }
  }, [reports]);

  return {
    users,
    activityLogs,
    reports,
    loading,
    getUsers,
    updateUser,
    deleteUser,
    bulkUpdateUsers,
    bulkDeleteUsers,
    getUserStatistics,
    getActivityLogs,
    getSystemHealth,
    getManuscriptReports,
    retryConversion,
    getConversionStatistics,
  };
};

export default useAdmin;
