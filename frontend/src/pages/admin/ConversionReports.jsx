import { useState, useEffect } from 'react';
import { getAllFiles, getAllUsers } from '../../utils/api';
import { useNotification } from '../../contexts/NotificationContext';
import Navigation from '../../components/shared/Navigation';
import Loading from '../../components/shared/Loading';
import * as XLSX from 'xlsx';

export const ConversionReports = () => {
  const { handleError, showSuccess } = useNotification();
  const [files, setFiles] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [dateRange, setDateRange] = useState({
    start: '',
    end: ''
  });

  useEffect(() => {
    loadReportData();
  }, []);

  const loadReportData = async () => {
    try {
      setLoading(true);
      const [filesResponse, usersResponse] = await Promise.all([
        getAllFiles(),
        getAllUsers()
      ]);

      setFiles(filesResponse.data?.files || []);
      setUsers(usersResponse.data?.users || []);
    } catch (error) {
      handleError(error, 'Failed to load report data');
    } finally {
      setLoading(false);
    }
  };

  const getUserName = (userId) => {
    const user = users.find(u => u.id === userId);
    return user ? user.username : 'Unknown';
  };

  const getUserEmail = (userId) => {
    const user = users.find(u => u.id === userId);
    return user ? user.email : 'N/A';
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFilteredFiles = () => {
    if (!dateRange.start && !dateRange.end) return files;

    return files.filter(file => {
      const fileDate = new Date(file.created_at);
      const startDate = dateRange.start ? new Date(dateRange.start) : null;
      const endDate = dateRange.end ? new Date(dateRange.end + 'T23:59:59') : null;

      if (startDate && fileDate < startDate) return false;
      if (endDate && fileDate > endDate) return false;
      return true;
    });
  };

  const exportToExcel = async () => {
    try {
      setExporting(true);

      const filteredFiles = getFilteredFiles();

      if (filteredFiles.length === 0) {
        handleError(new Error('No data to export'), 'No data available');
        return;
      }

      // Prepare data for Excel export
      const exportData = filteredFiles.map((file, index) => {
        const outputFormats = file.output_files 
          ? file.output_files.map(f => {
              const ext = f.split('.').pop().toUpperCase();
              return ext;
            }).join(', ')
          : 'N/A';

        return {
          'S.No': index + 1,
          'File Name': file.original_filename || 'Unknown',
          'File Size': formatFileSize(file.file_size),
          'Status': file.status ? file.status.toUpperCase() : 'UNKNOWN',
          'User Name': getUserName(file.user_id),
          'User Email': getUserEmail(file.user_id),
          'Upload Date': formatDate(file.created_at),
          'Last Updated': formatDate(file.updated_at),
          'Output Formats': outputFormats,
          'Output Files Count': file.output_files ? file.output_files.length : 0,
          'Processing Time': file.processing_time || 'N/A',
          'Error Message': file.error_message || 'None',
          'File ID': file.id,
          'Storage Path': file.file_path || 'N/A'
        };
      });

      // Create summary sheet data
      const summaryData = [
        { Metric: 'Total Files', Value: filteredFiles.length },
        { Metric: 'Completed Conversions', Value: filteredFiles.filter(f => f.status === 'completed').length },
        { Metric: 'Failed Conversions', Value: filteredFiles.filter(f => f.status === 'failed').length },
        { Metric: 'Processing Files', Value: filteredFiles.filter(f => f.status === 'processing' || f.status === 'uploaded').length },
        { Metric: 'Total Users', Value: users.length },
        { Metric: 'Report Generated', Value: new Date().toLocaleString() },
        { Metric: 'Date Range', Value: dateRange.start || dateRange.end ? `${dateRange.start || 'Beginning'} to ${dateRange.end || 'Present'}` : 'All Time' }
      ];

      // Create status breakdown
      const statusBreakdown = [
        { Status: 'Uploaded', Count: filteredFiles.filter(f => f.status === 'uploaded').length },
        { Status: 'Processing', Count: filteredFiles.filter(f => f.status === 'processing').length },
        { Status: 'Completed', Count: filteredFiles.filter(f => f.status === 'completed').length },
        { Status: 'Failed', Count: filteredFiles.filter(f => f.status === 'failed').length }
      ];

      // Create user activity breakdown
      const userActivity = users.map(user => {
        const userFiles = filteredFiles.filter(f => f.user_id === user.id);
        return {
          'User Name': user.username,
          'Email': user.email,
          'Role': user.role.toUpperCase(),
          'Total Files': userFiles.length,
          'Completed': userFiles.filter(f => f.status === 'completed').length,
          'Failed': userFiles.filter(f => f.status === 'failed').length,
          'Processing': userFiles.filter(f => f.status === 'processing' || f.status === 'uploaded').length
        };
      }).filter(u => u['Total Files'] > 0);

      // Create workbook
      const workbook = XLSX.utils.book_new();

      // Add Summary sheet
      const summarySheet = XLSX.utils.json_to_sheet(summaryData);
      XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary');

      // Add Status Breakdown sheet
      const statusSheet = XLSX.utils.json_to_sheet(statusBreakdown);
      XLSX.utils.book_append_sheet(workbook, statusSheet, 'Status Breakdown');

      // Add User Activity sheet
      const userSheet = XLSX.utils.json_to_sheet(userActivity);
      XLSX.utils.book_append_sheet(workbook, userSheet, 'User Activity');

      // Add Detailed Data sheet
      const detailSheet = XLSX.utils.json_to_sheet(exportData);
      XLSX.utils.book_append_sheet(workbook, detailSheet, 'Conversion Details');

      // Generate filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const filename = `R2_Conversion_Report_${timestamp}.xlsx`;

      // Write file
      XLSX.writeFile(workbook, filename);

      showSuccess('Export Successful', `Report exported as ${filename}`);

    } catch (error) {
      handleError(error, 'Failed to export report');
    } finally {
      setExporting(false);
    }
  };

  const filteredFiles = getFilteredFiles();

  const stats = {
    total: filteredFiles.length,
    completed: filteredFiles.filter(f => f.status === 'completed').length,
    failed: filteredFiles.filter(f => f.status === 'failed').length,
    processing: filteredFiles.filter(f => f.status === 'processing' || f.status === 'uploaded').length,
    totalSize: filteredFiles.reduce((sum, f) => sum + (f.file_size || 0), 0)
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-2">
            Conversion Reports
          </h1>
          <p className="text-gray-600">Generate and export detailed conversion reports</p>
        </div>

        {loading ? (
          <div className="py-20">
            <Loading />
          </div>
        ) : (
          <>
            {/* Export Controls */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Filter & Export</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Start Date
                      </label>
                      <input
                        type="date"
                        value={dateRange.start}
                        onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        End Date
                      </label>
                      <input
                        type="date"
                        value={dateRange.end}
                        onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  <button
                    onClick={exportToExcel}
                    disabled={exporting || stats.total === 0}
                    className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
                  >
                    {exporting ? (
                      <>
                        <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Exporting...
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Export to Excel
                      </>
                    )}
                  </button>
                  
                  {(dateRange.start || dateRange.end) && (
                    <button
                      onClick={() => setDateRange({ start: '', end: '' })}
                      className="px-6 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors"
                    >
                      Clear Filters
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-purple-500">
                <p className="text-sm font-medium text-gray-600 mb-1">Total Files</p>
                <p className="text-3xl font-bold text-purple-600">{stats.total}</p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-green-500">
                <p className="text-sm font-medium text-gray-600 mb-1">Completed</p>
                <p className="text-3xl font-bold text-green-600">{stats.completed}</p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-blue-500">
                <p className="text-sm font-medium text-gray-600 mb-1">Processing</p>
                <p className="text-3xl font-bold text-blue-600">{stats.processing}</p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-red-500">
                <p className="text-sm font-medium text-gray-600 mb-1">Failed</p>
                <p className="text-3xl font-bold text-red-600">{stats.failed}</p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-indigo-500">
                <p className="text-sm font-medium text-gray-600 mb-1">Total Size</p>
                <p className="text-2xl font-bold text-indigo-600">{formatFileSize(stats.totalSize)}</p>
              </div>
            </div>

            {/* Export Information */}
            <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl shadow-lg p-6 mb-8 text-white">
              <div className="flex items-start gap-4">
                <div className="bg-white bg-opacity-20 rounded-lg p-3">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold mb-2">Excel Export Information</h3>
                  <p className="text-purple-100 mb-3">
                    The exported Excel file will contain multiple sheets with comprehensive data:
                  </p>
                  <ul className="space-y-2 text-sm text-purple-100">
                    <li className="flex items-center gap-2">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span><strong>Summary:</strong> Overall statistics and metrics</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span><strong>Status Breakdown:</strong> Conversion status distribution</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span><strong>User Activity:</strong> Per-user conversion statistics</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span><strong>Conversion Details:</strong> Complete file information and validation data</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Recent Files Preview */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Files Preview</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Showing {filteredFiles.length} {filteredFiles.length === 1 ? 'file' : 'files'}
                  {(dateRange.start || dateRange.end) && ' (filtered)'}
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        File Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        User
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Size
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredFiles.slice(0, 10).map((file) => (
                      <tr key={file.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {file.original_filename}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {getUserName(file.user_id)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 text-xs font-semibold rounded-full ${
                            file.status === 'completed' ? 'bg-green-100 text-green-800' :
                            file.status === 'failed' ? 'bg-red-100 text-red-800' :
                            file.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}>
                            {file.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {formatFileSize(file.file_size)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(file.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {filteredFiles.length === 0 && (
                  <div className="text-center py-12">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No files found</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      {(dateRange.start || dateRange.end) 
                        ? 'Try adjusting your date range filter.'
                        : 'No conversion data available yet.'}
                    </p>
                  </div>
                )}

                {filteredFiles.length > 10 && (
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 text-center">
                    <p className="text-sm text-gray-600">
                      Showing first 10 of {filteredFiles.length} files. Export to Excel to view all data.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ConversionReports;