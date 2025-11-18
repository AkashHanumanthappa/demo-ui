import { useState, useCallback } from 'react';

export const useDownload = () => {
  const [downloads, setDownloads] = useState([]);
  const [history, setHistory] = useState(() => {
    const saved = localStorage.getItem('download_history');
    return saved ? JSON.parse(saved) : [];
  });

  const downloadFile = useCallback(async (url, fileName) => {
    const downloadId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const downloadItem = {
      id: downloadId,
      fileName,
      url,
      progress: 0,
      status: 'downloading',
      startTime: new Date(),
      speed: 0,
      timeRemaining: 0,
    };

    setDownloads((prev) => [...prev, downloadItem]);

    try {
      const response = await fetch(url);

      // Check if response is ok
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
      }

      // Check content-length to validate response
      const contentLength = response.headers.get('content-length');
      if (!contentLength || contentLength === '0') {
        console.warn('Warning: No content-length header or zero-length file');
      }

      const blob = await response.blob();

      // Validate blob size
      if (blob.size === 0) {
        throw new Error('Downloaded file is empty');
      }

      // Create download link
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up the blob URL after a short delay
      setTimeout(() => {
        window.URL.revokeObjectURL(link.href);
      }, 100);

      // Update download status
      setDownloads((prev) =>
        prev.map((d) => (d.id === downloadId ? { ...d, progress: 100, status: 'completed' } : d))
      );

      // Add to history
      const historyItem = {
        id: downloadId,
        fileName,
        url,
        timestamp: new Date(),
        status: 'completed',
      };

      setHistory((prev) => {
        const newHistory = [historyItem, ...prev].slice(0, 50); // Keep last 50
        localStorage.setItem('download_history', JSON.stringify(newHistory));
        return newHistory;
      });

      // Remove from active downloads after 3 seconds
      setTimeout(() => {
        setDownloads((prev) => prev.filter((d) => d.id !== downloadId));
      }, 3000);

      return true;
    } catch (error) {
      setDownloads((prev) =>
        prev.map((d) => (d.id === downloadId ? { ...d, status: 'failed', error: error.message } : d))
      );
      throw error;
    }
  }, []);

  const downloadMultipleFiles = useCallback(
    async (files) => {
      const promises = files.map((file) => downloadFile(file.url, file.fileName));
      return Promise.allSettled(promises);
    },
    [downloadFile]
  );

  const cancelDownload = useCallback((downloadId) => {
    setDownloads((prev) => prev.filter((d) => d.id !== downloadId));
  }, []);

  const cancelAllDownloads = useCallback(() => {
    setDownloads([]);
  }, []);

  const retryDownload = useCallback(
    (downloadId) => {
      const download = downloads.find((d) => d.id === downloadId);
      if (download) {
        return downloadFile(download.url, download.fileName);
      }
    },
    [downloads, downloadFile]
  );

  const clearDownloadHistory = useCallback(() => {
    localStorage.removeItem('download_history');
    setHistory([]);
  }, []);

  const getDownloadStatistics = useCallback(() => {
    const completed = history.filter((h) => h.status === 'completed').length;
    const failed = history.filter((h) => h.status === 'failed').length;
    return {
      total: history.length,
      completed,
      failed,
    };
  }, [history]);

  return {
    downloads,
    history,
    downloadFile,
    downloadMultipleFiles,
    cancelDownload,
    cancelAllDownloads,
    retryDownload,
    clearDownloadHistory,
    getDownloadStatistics,
  };
};

export default useDownload;
