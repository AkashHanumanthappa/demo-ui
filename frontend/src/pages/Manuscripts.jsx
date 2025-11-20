import { useState, useEffect, useRef } from 'react';
import { useManuscripts } from '../hooks/useManuscripts';
import { useDownload } from '../hooks/useDownload';
import { useNotification } from '../contexts/NotificationContext';
import Navigation from '../components/shared/Navigation';
import Loading from '../components/shared/Loading';
import FileUpload from '../components/shared/FileUpload';
import ConfirmationDialog from '../components/shared/ConfirmationDialog';
import { 
  CheckCircle, 
  Clock, 
  Upload, 
  FileText, 
  Download, 
  Trash2, 
  AlertCircle,
  File,
  ChevronRight,
  ChevronDown,
  RefreshCw
} from 'lucide-react';

export const Manuscripts = () => {
  const { manuscripts, loading, getManuscripts, uploadManuscript, deleteManuscript, getDownloadUrl, uploadProgress } = useManuscripts();
  const { downloadFile } = useDownload();
  const { showSuccess, showError, handleError } = useNotification();

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [expandedFile, setExpandedFile] = useState(null);
  const hasLoadedInitially = useRef(false);

  // Initial load - ONLY ONCE
  useEffect(() => {
    if (!hasLoadedInitially.current) {
      console.log('📥 Initial load of manuscripts');
      loadManuscripts();
      hasLoadedInitially.current = true;
    }
  }, []);

  const loadManuscripts = async () => {
    try {
      console.log('📂 Loading manuscripts from server...');
      await getManuscripts();
      console.log('✓ Manuscripts loaded successfully');
    } catch (error) {
      console.error('❌ Failed to load manuscripts:', error);
      handleError(error, 'Failed to load manuscripts');
    }
  };

  const handleFileSelect = async (file) => {
    setUploading(true);
    try {
      console.log('📤 Starting file upload:', file.name);
      const result = await uploadManuscript(file);
      
      console.log('✓ Upload result:', result);
      
      // REFRESH #1: Immediately after successful upload
      console.log('🔄 REFRESH #1: Loading manuscripts after upload...');
      await loadManuscripts();
      
      showSuccess(
        'Upload Successful', 
        `${file.name} has been uploaded successfully and is now being processed.`
      );
      
      setShowUploadModal(false);
      
    } catch (error) {
      console.error('❌ Upload failed:', error);
      
      // Check if it's a timeout error
      if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
        handleError(
          error, 
          'Upload Timeout - The file upload took too long. Please try again with a smaller file or check your internet connection.'
        );
      } else {
        handleError(error, 'Upload failed');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (manuscript, fileType) => {
    try {
      const urlData = await getDownloadUrl(manuscript.id, fileType);
      await downloadFile(urlData.download_url, `${manuscript.file_name}.${fileType}`);
      showSuccess('Download Started', `Downloading ${fileType} file`);
    } catch (error) {
      handleError(error, 'Download failed');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;

    try {
      await deleteManuscript(deleteConfirm.id);
      showSuccess('Deleted', `${deleteConfirm.file_name} has been deleted`);
      setDeleteConfirm(null);
      setExpandedFile(null);
      // Refresh list after delete
      await loadManuscripts();
    } catch (error) {
      handleError(error, 'Delete failed');
    }
  };

  const handleManualRefresh = async () => {
    console.log('🔄 Manual refresh triggered');
    await loadManuscripts();
    showSuccess('Refreshed', 'Manuscripts list has been updated');
  };

  const toggleFileExpand = (manuscriptId) => {
    setExpandedFile(expandedFile === manuscriptId ? null : manuscriptId);
  };

  const getStatusInfo = (status) => {
    const statusMap = {
      uploaded: {
        color: 'text-blue-700',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        icon: Clock,
        label: 'Processing',
        description: 'Converting file formats'
      },
      processing: {
        color: 'text-blue-700',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        icon: Clock,
        label: 'Processing',
        description: 'Converting file formats'
      },
      completed: {
        color: 'text-success-700',
        bgColor: 'bg-success-50',
        borderColor: 'border-success-200',
        icon: CheckCircle,
        label: 'Completed',
        description: 'Ready for download'
      },
      failed: {
        color: 'text-error-700',
        bgColor: 'bg-error-50',
        borderColor: 'border-error-200',
        icon: AlertCircle,
        label: 'Failed',
        description: 'Conversion failed'
      },
    };
    return statusMap[status] || statusMap.processing;
  };

  const getTrackingSteps = (status) => {
    const steps = [
      { id: 'uploaded', label: 'Uploaded', icon: Upload },
      { id: 'processing', label: 'Processing', icon: Clock },
      { id: 'completed', label: 'Completed', icon: CheckCircle }
    ];

    const statusOrder = ['uploaded', 'processing', 'completed', 'failed'];
    const currentIndex = statusOrder.indexOf(status);

    return steps.map((step, index) => ({
      ...step,
      isCompleted: index < currentIndex || (status === 'completed' && index <= 2),
      isCurrent: step.id === status || (status === 'failed' && step.id === 'completed'),
      isFailed: status === 'failed' && step.id === 'completed'
    }));
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const filteredManuscripts = manuscripts.filter((m) => {
    const matchesSearch = m.file_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || m.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const hasProcessingFiles = manuscripts.some(
    m => m.status === 'processing' || m.status === 'uploaded'
  );

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(to bottom right, #e8f0f8, #f5f9fc)' }}>
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header - Responsive */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 sm:mb-8 gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-1 sm:mb-2">Manuscript Library</h1>
            <p className="text-sm sm:text-base text-gray-600">Manage and convert your digital manuscripts</p>
          </div>
          <div className="flex gap-2 sm:gap-3 w-full sm:w-auto">
            {/* Manual Refresh Button */}
            <button
              onClick={handleManualRefresh}
              disabled={loading}
              className="flex items-center justify-center gap-2 px-3 sm:px-4 py-2 sm:py-3 rounded-lg font-semibold border-2 transition-all duration-200 hover:scale-105 flex-1 sm:flex-initial"
              style={{
                backgroundColor: loading ? '#e0e0e0' : '#e8f3f9',
                borderColor: '#6890b8',
                color: '#4f7299'
              }}
            >
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              <span className="text-sm sm:text-base">Refresh</span>
            </button>

            <button
              onClick={() => setShowUploadModal(true)}
              className="flex items-center justify-center gap-2 text-white px-4 sm:px-6 py-2 sm:py-3 rounded-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 flex-1 sm:flex-initial"
              style={{
                backgroundColor: '#4f7299',
                border: '2px solid #3d5b7a'
              }}
            >
              <Upload size={18} />
              <span className="text-sm sm:text-base">Upload</span>
            </button>
          </div>
        </div>

        {/* Info Banner - Processing Files */}
        {hasProcessingFiles && (
          <div className="mb-6 p-4 rounded-lg border-2" style={{
            backgroundColor: '#e8f3f9',
            borderColor: '#6890b8'
          }}>
            <div className="flex items-start gap-3">
              <Clock size={20} style={{ color: '#4f7299' }} className="flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-sm mb-1" style={{ color: '#2c3e50' }}>
                  Files Being Processed
                </p>
                <p className="text-sm" style={{ color: '#6890b8' }}>
                  Your files are being converted. Click the <strong>"Refresh"</strong> button above to check for updates.
                  The page will also automatically refresh when you upload a new file.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Search and Filter */}
        <div className="bg-white rounded-xl shadow-card border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="relative">
              <input
                type="text"
                placeholder="Search manuscripts by name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent transition-all"
                style={{ '--tw-ring-color': '#6890b8' }}
              />
              <FileText className="absolute left-3 top-3.5 text-gray-400" size={20} />
            </div>
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:border-transparent transition-all"
                style={{ '--tw-ring-color': '#6890b8' }}
              >
                <option value="all">All Status</option>
                <option value="uploaded">Processing (Uploaded)</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>

        {/* Manuscripts List */}
        <div className="space-y-3">
          {loading ? (
            <div className="bg-white rounded-xl shadow-card border border-gray-200 p-12">
              <Loading />
            </div>
          ) : filteredManuscripts.length === 0 ? (
            <div className="bg-white rounded-xl shadow-card border border-gray-200 p-12 text-center">
              <File size={48} className="mx-auto text-gray-400 mb-4" />
              <p className="text-gray-500 text-lg">No manuscripts found</p>
              <p className="text-gray-400 text-sm mt-2">Upload your first manuscript to get started</p>
            </div>
          ) : (
            filteredManuscripts.map((manuscript) => {
              const statusInfo = getStatusInfo(manuscript.status);
              const trackingSteps = getTrackingSteps(manuscript.status);
              const StatusIcon = statusInfo.icon;
              const isExpanded = expandedFile === manuscript.id;

              return (
                <div
                  key={manuscript.id}
                  className="bg-white rounded-xl shadow-card border border-gray-200 hover:shadow-card-hover transition-all duration-200 animate-slide-in overflow-hidden"
                >
                  {/* Input File Row - Responsive */}
                  <div
                    onClick={() => toggleFileExpand(manuscript.id)}
                    className="p-4 sm:p-6 cursor-pointer hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                      {/* Mobile: Icon + Filename Row */}
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div className="flex-shrink-0">
                          {isExpanded ? (
                            <ChevronDown size={20} className="sm:w-6 sm:h-6" style={{ color: '#4f7299' }} />
                          ) : (
                            <ChevronRight size={20} className="sm:w-6 sm:h-6 text-gray-400" />
                          )}
                        </div>

                        <div className="flex-shrink-0">
                          <File className="text-primary-600 w-6 h-6 sm:w-8 sm:h-8" style={{ color: '#4f7299' }} />
                        </div>

                        <div className="flex-1 min-w-0">
                          <h3 className="text-base sm:text-lg font-semibold text-gray-900 break-all mb-2">
                            {manuscript.file_name}
                          </h3>
                          <div className="flex flex-wrap gap-2 sm:gap-3 text-xs sm:text-sm text-gray-600">
                            <span className="flex items-center gap-1">
                              <strong>Size:</strong> {formatFileSize(manuscript.file_size)}
                            </span>
                            <span className="flex items-center gap-1">
                              <strong>Format:</strong> {manuscript.original_format?.toUpperCase() || 'N/A'}
                            </span>
                            <span className="flex items-center gap-1 hidden sm:flex">
                              <strong>Uploaded:</strong> {new Date(manuscript.created_at).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                          {/* Mobile date - separate line */}
                          <div className="mt-1 text-xs text-gray-500 sm:hidden">
                            {new Date(manuscript.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                        </div>
                      </div>

                      {/* Status Badge - Stacked on mobile */}
                      <div className={`flex items-center justify-center gap-2 px-3 sm:px-4 py-2 rounded-full ${statusInfo.bgColor} border ${statusInfo.borderColor} self-start sm:self-center`}>
                        <StatusIcon size={16} className={`sm:w-5 sm:h-5 ${statusInfo.color}`} />
                        <span className={`font-semibold text-xs sm:text-sm ${statusInfo.color}`}>
                          {statusInfo.label}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="border-t border-gray-200 bg-gray-50 p-6 animate-slide-in">
                      {/* Tracking Progress */}
                      <div className="mb-6">
                        <h4 className="text-sm font-semibold text-gray-700 mb-4">Processing Status</h4>
                        <div className="relative">
                          <div className="flex items-center justify-between">
                            {trackingSteps.map((step, index) => {
                              const StepIcon = step.icon;
                              return (
                                <div key={step.id} className="flex-1">
                                  <div className="flex items-center">
                                    <div className="relative flex flex-col items-center">
                                      <div
                                        className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                                          step.isFailed
                                            ? 'bg-error-100 border-error-500 text-error-600'
                                            : step.isCompleted
                                            ? 'bg-success-100 border-success-500 text-success-600'
                                            : step.isCurrent
                                            ? 'border-2 text-white'
                                            : 'bg-gray-100 border-gray-300 text-gray-400'
                                        }`}
                                        style={step.isCurrent ? {
                                          backgroundColor: '#6890b8',
                                          borderColor: '#4f7299'
                                        } : {}}
                                      >
                                        <StepIcon size={24} />
                                      </div>
                                      <span
                                        className={`mt-2 text-sm font-medium ${
                                          step.isFailed
                                            ? 'text-error-600'
                                            : step.isCompleted || step.isCurrent
                                            ? 'text-gray-900'
                                            : 'text-gray-500'
                                        }`}
                                      >
                                        {step.isFailed && step.id === 'completed' ? 'Failed' : step.label}
                                      </span>
                                    </div>

                                    {index < trackingSteps.length - 1 && (
                                      <div className="flex-1 h-0.5 mx-2 relative top-[-20px]">
                                        <div
                                          className={`h-full transition-all duration-500 ${
                                            step.isCompleted ? 'bg-success-500' : 'bg-gray-300'
                                          }`}
                                        />
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>

                      {/* Processing Notice */}
                      {(manuscript.status === 'processing' || manuscript.status === 'uploaded') && (
                        <div className="mb-6 p-4 rounded-lg border-2" style={{
                          backgroundColor: '#e8f3f9',
                          borderColor: '#6890b8'
                        }}>
                          <div className="flex items-start gap-2">
                            <Clock size={18} style={{ color: '#4f7299' }} className="flex-shrink-0 mt-0.5" />
                            <div>
                              <p className="font-semibold text-sm" style={{ color: '#2c3e50' }}>
                                ⏳ Conversion in Progress
                              </p>
                              <p className="text-sm mt-1" style={{ color: '#6890b8' }}>
                                Your file is being processed. Click the <strong>"Refresh"</strong> button above to check for updates.
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Error Message */}
                      {manuscript.status === 'failed' && manuscript.error_message && (
                        <div className="mb-6 p-4 bg-error-50 border border-error-200 rounded-lg">
                          <div className="flex items-start gap-2">
                            <AlertCircle className="text-error-600 flex-shrink-0 mt-0.5" size={18} />
                            <div>
                              <p className="font-semibold text-error-900 text-sm">Error Details:</p>
                              <p className="text-error-700 text-sm mt-1">{manuscript.error_message}</p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Action Sections */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Download Section */}
                        <div className="border-2 rounded-lg p-4" style={{ 
                          backgroundColor: '#e8f3f9',
                          borderColor: '#6890b8'
                        }}>
                          <div className="flex items-center gap-2 mb-3">
                            <Download size={20} style={{ color: '#4f7299' }} />
                            <h4 className="font-semibold text-gray-900">Download Output Files</h4>
                          </div>
                          {manuscript.status === 'completed' && manuscript.output_files?.length > 0 ? (
                            <div className="space-y-2">
                              {manuscript.output_files.map((file, index) => {
                                const fileExt = file.fileName.split('.').pop().toUpperCase();
                                return (
                                  <button
                                    key={index}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDownload(manuscript, file.fileName);
                                    }}
                                    className="w-full flex items-center justify-between px-4 py-3 bg-white rounded-lg hover:bg-blue-50 transition-all duration-200 group"
                                    style={{
                                      border: '1px solid #6890b8'
                                    }}
                                  >
                                    <div className="flex items-center gap-3">
                                      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#e8f3f9' }}>
                                        <FileText size={20} style={{ color: '#4f7299' }} />
                                      </div>
                                      <div className="text-left">
                                        <p className="font-semibold text-gray-900 text-sm break-all">
                                          {file.fileName}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                          {fileExt} Format • {formatFileSize(file.fileSize)}
                                        </p>
                                      </div>
                                    </div>
                                    <ChevronRight className="group-hover:translate-x-1 transition-transform" size={20} style={{ color: '#4f7299' }} />
                                  </button>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="text-center py-4">
                              {(manuscript.status === 'processing' || manuscript.status === 'uploaded') && (
                                <Clock className="mx-auto text-gray-400 mb-2" size={24} />
                              )}
                              <p className="text-sm text-gray-600">
                                {manuscript.status === 'processing' || manuscript.status === 'uploaded'
                                  ? 'Files will be available after processing'
                                  : manuscript.status === 'failed'
                                  ? 'No files available due to error'
                                  : 'Processing not started'}
                              </p>
                            </div>
                          )}
                        </div>

                        {/* Delete Section */}
                        <div className="bg-gradient-delete border-2 border-error-200 rounded-lg p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <Trash2 className="text-error-600" size={20} />
                            <h4 className="font-semibold text-gray-900">Delete Manuscript</h4>
                          </div>
                          <div className="text-center py-4">
                            <p className="text-sm text-gray-600 mb-4">
                              Permanently remove this manuscript and all files
                            </p>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteConfirm(manuscript);
                              }}
                              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white hover:bg-error-50 border-2 border-error-300 hover:border-error-400 text-error-600 rounded-lg font-semibold transition-all duration-200"
                            >
                              <Trash2 size={18} />
                              Delete Manuscript
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity bg-gray-900 bg-opacity-75 backdrop-blur-sm"
              onClick={() => !uploading && setShowUploadModal(false)}
            ></div>
            <div className="inline-block align-bottom bg-white rounded-2xl px-4 pt-5 pb-4 text-left overflow-hidden shadow-2xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ backgroundColor: '#e8f3f9' }}>
                  <Upload size={24} style={{ color: '#4f7299' }} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Upload Manuscript</h3>
                  <p className="text-sm text-gray-600">Select a PDF or EPUB file to upload</p>
                </div>
              </div>
              {uploading ? (
                <div className="py-8">
                  <Loading text="Uploading your manuscript..." />
                  {Object.values(uploadProgress).map((progress, index) => (
                    <div key={index} className="mt-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-2">
                        <span>Upload Progress</span>
                        <span>{progress.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                          className="h-2.5 rounded-full transition-all duration-300 progress-bar-striped animate-progress-bar"
                          style={{ width: `${progress.progress}%`, backgroundColor: '#6890b8' }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <>
                  <FileUpload onFileSelect={handleFileSelect} accept=".pdf,.epub" maxSize={524288000} />
                  <div className="mt-6 flex gap-3">
                    <button
                      type="button"
                      onClick={() => setShowUploadModal(false)}
                      className="flex-1 px-4 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      <ConfirmationDialog
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        onConfirm={handleDelete}
        title="Delete Manuscript"
        message={`Are you sure you want to delete "${deleteConfirm?.file_name}"? This action cannot be undone.`}
        confirmText="Delete Permanently"
        type="danger"
      />
    </div>
  );
};

export default Manuscripts;