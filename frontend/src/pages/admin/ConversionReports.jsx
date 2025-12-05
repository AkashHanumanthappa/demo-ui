import { useState, useEffect, useRef } from 'react';
import { getConversionDashboardFiles } from '../../utils/api';
import { useNotification } from '../../contexts/NotificationContext';
import Navigation from '../../components/shared/Navigation';
import Loading from '../../components/shared/Loading';
import * as XLSX from 'xlsx';
import axios from 'axios';

export const ConversionDashboard = () => {
  const { handleError, showSuccess } = useNotification();
  const [dashboardFiles, setDashboardFiles] = useState([]);
  const [allExcelData, setAllExcelData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFileType, setSelectedFileType] = useState('all');
  const [availableFileTypes, setAvailableFileTypes] = useState([]);
  
  // Sorting state
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc'); // 'asc' or 'desc'
  const [openColumnMenu, setOpenColumnMenu] = useState(null);
  
  const menuRef = useRef(null);

  useEffect(() => {
    loadDashboardFiles();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [searchTerm, selectedFileType, allExcelData, sortColumn, sortDirection]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpenColumnMenu(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadDashboardFiles = async () => {
    try {
      setLoading(true);
      console.log('🔍 Fetching conversion dashboard files...');
      
      const response = await getConversionDashboardFiles();
      const files = response.data?.files || [];
      console.log(`✅ Found ${files.length} files`);
      
      setDashboardFiles(files);
      
      // Extract unique file types
      const fileTypes = new Set();
      files.forEach(file => {
        if (file.fileType) {
          fileTypes.add(file.fileType.toUpperCase());
        }
      });
      setAvailableFileTypes(Array.from(fileTypes).sort());
      
      // Load all Excel files
      if (files.length > 0) {
        await loadAllExcelFiles(files);
      }
      
    } catch (error) {
      console.error('❌ Error loading dashboard files:', error);
      handleError(error, 'Failed to load dashboard files');
    } finally {
      setLoading(false);
    }
  };

  const loadAllExcelFiles = async (files) => {
    try {
      const allData = [];
      const sheets = new Set();

      for (const file of files) {
        console.log('📂 Loading file:', file.originalName);

        const fileToDownload = file.outputFiles?.find(f => 
          f.fileName === 'conversion_dashboard.xlsx'
        );
        
        if (!fileToDownload) {
          console.warn('⚠️ No conversion_dashboard.xlsx in:', file.originalName);
          continue;
        }

        const token = localStorage.getItem('manuscript_token');
        const apiUrl = 'http://localhost:5000/api';
        const downloadUrl = `${apiUrl}/files/${file._id}/download/${encodeURIComponent(fileToDownload.fileName)}`;

        const response = await axios.get(downloadUrl, {
          responseType: 'arraybuffer',
          headers: { 'Authorization': `Bearer ${token}` }
        });

        const data = new Uint8Array(response.data);
        const workbook = XLSX.read(data, { type: 'array' });

        workbook.SheetNames.forEach((sheetName) => {
          sheets.add(sheetName);
          const worksheet = workbook.Sheets[sheetName];
          const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
            header: 1,
            defval: '',
            blankrows: false
          });

          if (jsonData.length > 1) {
            const headers = jsonData[0];
            const rows = jsonData.slice(1);

            rows.forEach((row) => {
              const rowData = {
                fileName: file.originalName,
                fileId: file._id,
                fileType: file.fileType ? file.fileType.toUpperCase() : 'UNKNOWN',
                sheetName: sheetName,
                uploadedBy: file.uploadedBy?.username || 'Unknown',
                uploadDate: file.createdAt,
                ...Object.fromEntries(
                  headers.map((header, index) => [header, row[index]])
                )
              };
              allData.push(rowData);
            });
          }
        });
      }

      console.log('✅ Loaded all Excel data:', allData.length, 'rows');
      setAllExcelData(allData);
      setFilteredData(allData);

    } catch (error) {
      console.error('❌ Error loading Excel files:', error);
      handleError(error, 'Failed to load Excel files');
    }
  };

  const applyFilters = () => {
    let filtered = [...allExcelData];

    // Filter by file type
    if (selectedFileType !== 'all') {
      filtered = filtered.filter(row => row.fileType === selectedFileType);
    }

    // Filter by search term
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(row => {
        return Object.values(row).some(value => 
          value && value.toString().toLowerCase().includes(search)
        );
      });
    }

    // Apply sorting
    if (sortColumn) {
      filtered.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];

        // Handle null/undefined values
        if (aVal === null || aVal === undefined || aVal === '') aVal = '';
        if (bVal === null || bVal === undefined || bVal === '') bVal = '';

        // Convert to comparable values
        if (typeof aVal === 'string') aVal = aVal.toLowerCase();
        if (typeof bVal === 'string') bVal = bVal.toLowerCase();

        // Compare
        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
      });
    }

    setFilteredData(filtered);
  };

  const handleSort = (column, direction) => {
    setSortColumn(column);
    setSortDirection(direction);
    setOpenColumnMenu(null);
    showSuccess(`Sorted by ${column} (${direction === 'asc' ? 'A→Z' : 'Z→A'})`);
  };

  const clearSort = () => {
    setSortColumn(null);
    setSortDirection('asc');
    setOpenColumnMenu(null);
    showSuccess('Sorting cleared');
  };

  const formatCellValue = (value) => {
    if (value === null || value === undefined || value === '') return '-';
    if (typeof value === 'number') return value.toLocaleString();
    if (value instanceof Date) return value.toLocaleDateString();
    return String(value);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const exportToExcel = () => {
    if (filteredData.length === 0) {
      showSuccess('No data to export');
      return;
    }

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(filteredData);
    XLSX.utils.book_append_sheet(wb, ws, 'Dashboard Data');
    
    const fileName = `conversion_dashboard_export_${new Date().toISOString().slice(0, 10)}.xlsx`;
    XLSX.writeFile(wb, fileName);
    showSuccess(`Exported ${filteredData.length} rows to ${fileName}`);
  };

  const clearFilters = () => {
    setSearchTerm('');
    setSelectedFileType('all');
    setSortColumn(null);
    setSortDirection('asc');
  };

  // Get all unique column headers
  const getTableHeaders = () => {
    if (filteredData.length === 0) return [];
    
    const allKeys = new Set();
    filteredData.forEach(row => {
      Object.keys(row).forEach(key => {
        if (!['fileId'].includes(key)) {
          allKeys.add(key);
        }
      });
    });
    
    return Array.from(allKeys);
  };

  const headers = getTableHeaders();

  // Get file type badge color
  const getFileTypeBadgeColor = (fileType) => {
    const colors = {
      'EPUB': 'bg-purple-100 text-purple-800',
      'PDF': 'bg-red-100 text-red-800',
      'DOCX': 'bg-blue-100 text-blue-800',
      'XML': 'bg-green-100 text-green-800',
      'HTML': 'bg-orange-100 text-orange-800',
    };
    return colors[fileType] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-2">
                Conversion Dashboard
              </h1>
              <p className="text-gray-600">View and analyze all conversion dashboard data</p>
            </div>
            <button
              onClick={loadDashboardFiles}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
            >
              <svg className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {loading ? (
          <div className="py-20">
            <Loading />
          </div>
        ) : (
          <>
            {/* Filters Section */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {/* Search */}
                <div className="md:col-span-1">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Search in all columns..."
                      className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                    <svg className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                </div>

                {/* File Type Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    File Type
                  </label>
                  <select
                    value={selectedFileType}
                    onChange={(e) => setSelectedFileType(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value="all">All Types ({availableFileTypes.length})</option>
                    {availableFileTypes.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 items-end">
                  <button
                    onClick={clearFilters}
                    className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    Clear Filters
                  </button>
                  <button
                    onClick={exportToExcel}
                    disabled={filteredData.length === 0}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Export
                  </button>
                </div>
              </div>

              {/* Stats */}
              <div className="pt-4 border-t border-gray-200">
                <div className="flex flex-wrap items-center gap-6 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="font-medium">{allExcelData.length}</span> total rows
                  </div>
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                    </svg>
                    <span className="font-medium">{filteredData.length}</span> filtered rows
                  </div>
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    <span className="font-medium">{dashboardFiles.length}</span> files
                  </div>
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    <span className="font-medium">{availableFileTypes.length}</span> file types
                  </div>
                  {sortColumn && (
                    <div className="flex items-center gap-2 text-xs bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-medium">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
                      </svg>
                      Sorted by: {sortColumn} ({sortDirection === 'asc' ? 'A→Z' : 'Z→A'})
                    </div>
                  )}
                  {(searchTerm || selectedFileType !== 'all') && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-3 py-1 rounded-full font-medium">
                      Filters Active
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="overflow-x-auto">
                {filteredData.length === 0 ? (
                  <div className="text-center py-16">
                    <svg className="mx-auto h-16 w-16 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-4 text-lg font-medium text-gray-900">No Data Found</h3>
                    <p className="mt-2 text-sm text-gray-500">
                      {allExcelData.length === 0 
                        ? 'No conversion dashboard files available.' 
                        : 'Try adjusting your filters.'}
                    </p>
                  </div>
                ) : (
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gradient-to-r from-purple-600 to-blue-600 sticky top-0 z-10">
                      <tr>
                        {headers.map((header, index) => (
                          <th
                            key={index}
                            className="px-6 py-3 text-left text-xs font-bold text-white uppercase tracking-wider whitespace-nowrap relative group"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="flex items-center gap-2">
                                {header}
                                {sortColumn === header && (
                                  <svg 
                                    className="w-4 h-4" 
                                    fill="none" 
                                    stroke="currentColor" 
                                    viewBox="0 0 24 24"
                                  >
                                    {sortDirection === 'asc' ? (
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                    ) : (
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    )}
                                  </svg>
                                )}
                              </span>
                              
                              {/* Three Dots Menu */}
                              <div className="relative" ref={openColumnMenu === header ? menuRef : null}>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setOpenColumnMenu(openColumnMenu === header ? null : header);
                                  }}
                                  className="p-1 hover:bg-white/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                                >
                                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
                                  </svg>
                                </button>

                                {/* Dropdown Menu */}
                                {openColumnMenu === header && (
                                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                                    <button
                                      onClick={() => handleSort(header, 'asc')}
                                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-purple-50 flex items-center gap-3"
                                    >
                                      <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                      </svg>
                                      Sort A → Z (Ascending)
                                    </button>
                                    
                                    <button
                                      onClick={() => handleSort(header, 'desc')}
                                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-purple-50 flex items-center gap-3"
                                    >
                                      <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                      </svg>
                                      Sort Z → A (Descending)
                                    </button>

                                    {sortColumn === header && (
                                      <>
                                        <hr className="my-2 border-gray-200" />
                                        <button
                                          onClick={clearSort}
                                          className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-3"
                                        >
                                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                          </svg>
                                          Clear Sort
                                        </button>
                                      </>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {filteredData.map((row, rowIndex) => (
                        <tr key={rowIndex} className="hover:bg-gray-50 transition-colors">
                          {headers.map((header, colIndex) => (
                            <td
                              key={colIndex}
                              className="px-6 py-4 text-sm text-gray-900 whitespace-nowrap"
                            >
                              {header === 'fileType' ? (
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getFileTypeBadgeColor(row[header])}`}>
                                  {formatCellValue(row[header])}
                                </span>
                              ) : header === 'uploadDate' ? (
                                formatDate(row[header])
                              ) : (
                                formatCellValue(row[header])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Pagination Info */}
              {filteredData.length > 0 && (
                <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
                  <p className="text-sm text-gray-600 text-center">
                    Showing {filteredData.length} of {allExcelData.length} rows
                    {sortColumn && (
                      <span className="ml-2 text-purple-600">
                        • Sorted by {sortColumn} ({sortDirection === 'asc' ? 'Ascending' : 'Descending'})
                      </span>
                    )}
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ConversionDashboard;
