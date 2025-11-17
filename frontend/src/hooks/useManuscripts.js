import { useState, useCallback } from 'react';
import api from '../utils/api';
import environment from '../config/environment';

export const useManuscripts = () => {
  const [manuscripts, setManuscripts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  const getManuscripts = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      const response = await api.get('/files', { params });

      // Transform backend data to match frontend format
      const transformedFiles = response.data.files.map(file => ({
        id: file._id,
        file_name: file.originalName,
        file_size: file.fileSize,
        original_format: file.fileType,
        status: file.status,
        created_at: file.createdAt,
        updated_at: file.updatedAt,
        conversion_time: file.conversionMetadata?.processingTime,
        error_message: file.errorMessage,
        output_formats: file.outputFiles?.map(f => f.fileType) || [],
        output_files: file.outputFiles || [],
      }));

      setManuscripts(transformedFiles);
      return {
        manuscripts: transformedFiles,
        total: response.data.count,
      };
    } catch (error) {
      console.error('Failed to fetch manuscripts:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadManuscript = useCallback(
    async (file) => {
      try {
        const formData = new FormData();
        formData.append('file', file);

        const manuscriptId = `temp-${Date.now()}`;

        // Upload with progress tracking
        const response = await api.post('/files/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress((prev) => ({
              ...prev,
              [manuscriptId]: {
                progress,
                loaded: progressEvent.loaded,
                total: progressEvent.total,
              },
            }));
          },
        });

        const uploadedFile = response.data.file;

        // Transform backend response to frontend format
        const newManuscript = {
          id: uploadedFile._id,
          file_name: uploadedFile.originalName,
          file_size: uploadedFile.fileSize,
          original_format: uploadedFile.fileType,
          status: uploadedFile.status,
          created_at: uploadedFile.createdAt,
          updated_at: uploadedFile.updatedAt,
          conversion_time: uploadedFile.conversionMetadata?.processingTime,
          error_message: uploadedFile.errorMessage,
          output_formats: uploadedFile.outputFiles?.map(f => f.fileType) || [],
          output_files: uploadedFile.outputFiles || [],
        };

        // Add to manuscripts list
        setManuscripts((prev) => [newManuscript, ...prev]);

        // Clear upload progress
        setTimeout(() => {
          setUploadProgress((prev) => {
            const newProgress = { ...prev };
            delete newProgress[manuscriptId];
            return newProgress;
          });
        }, 1000);

        return newManuscript;
      } catch (error) {
        console.error('Upload failed:', error);
        throw new Error(error.response?.data?.message || error.message || 'Upload failed');
      }
    },
    []
  );

  const getDownloadUrl = useCallback(async (manuscriptId, fileName) => {
    try {
      // Find the manuscript to get the correct output file
      const manuscript = manuscripts.find(m => m.id === manuscriptId);
      if (!manuscript) {
        throw new Error('Manuscript not found');
      }

      // For now, return the download URL that will trigger the download
      const downloadUrl = `${environment.apiUrl}/files/${manuscriptId}/download/${fileName}`;

      return {
        download_url: downloadUrl,
        file_name: fileName,
        expires_at: new Date(Date.now() + 3600000).toISOString(),
      };
    } catch (error) {
      console.error('Failed to get download URL:', error);
      throw error;
    }
  }, [manuscripts]);

  const deleteManuscript = useCallback(
    async (manuscriptId) => {
      try {
        await api.delete(`/files/${manuscriptId}`);
        setManuscripts((prev) => prev.filter((m) => m.id !== manuscriptId));
      } catch (error) {
        console.error('Failed to delete manuscript:', error);
        throw new Error(error.response?.data?.message || error.message || 'Failed to delete manuscript');
      }
    },
    []
  );

  const getStatistics = useCallback(async () => {
    try {
      // Calculate statistics from current manuscripts
      const completed = manuscripts.filter(m => m.status === 'completed');
      const processing = manuscripts.filter(m => m.status === 'processing');
      const failed = manuscripts.filter(m => m.status === 'failed');

      const totalConversionTime = completed.reduce((sum, m) => sum + (m.conversion_time || 0), 0);
      const avgConversionTime = completed.length > 0 ? totalConversionTime / completed.length : 0;
      const successRate = manuscripts.length > 0 ? (completed.length / manuscripts.length) * 100 : 0;

      const stats = {
        total_manuscripts: manuscripts.length,
        completed: completed.length,
        processing: processing.length,
        failed: failed.length,
        total_size: manuscripts.reduce((sum, m) => sum + (m.file_size || 0), 0),
        average_conversion_time: avgConversionTime,
        success_rate: successRate,
      };

      return stats;
    } catch (error) {
      console.error('Failed to get statistics:', error);
      throw error;
    }
  }, [manuscripts]);

  return {
    manuscripts,
    loading,
    uploadProgress,
    getManuscripts,
    uploadManuscript,
    getDownloadUrl,
    deleteManuscript,
    getStatistics,
  };
};

export default useManuscripts;
