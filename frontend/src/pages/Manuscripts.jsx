import { useState, useEffect } from 'react';
import { useManuscripts } from '../hooks/useManuscripts';
import { useDownload } from '../hooks/useDownload';
import { useNotification } from '../contexts/NotificationContext';
import Navigation from '../components/shared/Navigation';
import Loading from '../components/shared/Loading';
import FileUpload from '../components/shared/FileUpload';
import ConfirmationDialog from '../components/shared/ConfirmationDialog';

export const Manuscripts = () => {
  const { manuscripts, loading, getManuscripts, uploadManuscript, deleteManuscript, getDownloadUrl } = useManuscripts();
  const { downloadFile } = useDownload();
  const { showSuccess, showError, handleError } = useNotification();

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  useEffect(() => {
    loadManuscripts();
    const interval = setInterval(loadManuscripts, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadManuscripts = async () => {
    try {
      await getManuscripts();
    } catch (error) {
      handleError(error, 'Failed to load manuscripts');
    }
  };

  const handleFileSelect = async (file) => {
    setUploading(true);
    try {
      await uploadManuscript(file);
      showSuccess('Upload Successful', `${file.name} has been uploaded successfully`);
      setShowUploadModal(false);
    } catch (error) {
      handleError(error, 'Upload failed');
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
    } catch (error) {
      handleError(error, 'Delete failed');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      uploaded: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const filteredManuscripts = manuscripts.filter((m) => {
    const matchesSearch = m.file_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || m.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="min-h-screen bg-secondary-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-secondary-900">Manuscripts</h1>
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-primary"
          >
            Upload Manuscript
          </button>
        </div>

        <div className="card mb-6 p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <input
                type="text"
                placeholder="Search manuscripts..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="input-field"
              >
                <option value="all">All Status</option>
                <option value="uploaded">Uploaded</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>

        <div className="card">
          {loading ? (
            <Loading />
          ) : filteredManuscripts.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-secondary-500">No manuscripts found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-secondary-200">
                <thead className="bg-secondary-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-600 uppercase tracking-wider">
                      File Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-600 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-600 uppercase tracking-wider">
                      Upload Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-600 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-secondary-200">
                  {filteredManuscripts.map((manuscript) => (
                    <tr key={manuscript.id} className="hover:bg-secondary-50 transition">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-secondary-900">
                        {manuscript.file_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(manuscript.status)}`}
                        >
                          {manuscript.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-600">
                        {new Date(manuscript.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        {manuscript.status === 'completed' && manuscript.output_files?.length > 0 && (
                          <>
                            {manuscript.output_files.map((file, index) => (
                              <button
                                key={index}
                                onClick={() => handleDownload(manuscript, file.fileName)}
                                className="text-primary-600 hover:text-primary-700 transition font-medium"
                              >
                                {file.fileName.split('.').pop().toUpperCase()}
                              </button>
                            ))}
                          </>
                        )}
                        <button
                          onClick={() => setDeleteConfirm(manuscript)}
                          className="text-red-600 hover:text-red-700 transition font-medium"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {showUploadModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity bg-secondary-900 bg-opacity-75"
              onClick={() => !uploading && setShowUploadModal(false)}
            ></div>
            <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <h3 className="text-lg leading-6 font-semibold text-secondary-900 mb-4">
                Upload Manuscript
              </h3>
              {uploading ? (
                <Loading text="Uploading..." />
              ) : (
                <>
                  <FileUpload onFileSelect={handleFileSelect} accept=".pdf,.epub" maxSize={524288000} />
                  <div className="mt-5 sm:mt-6">
                    <button
                      type="button"
                      onClick={() => setShowUploadModal(false)}
                      className="btn-secondary w-full justify-center"
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

      <ConfirmationDialog
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        onConfirm={handleDelete}
        title="Delete Manuscript"
        message={`Are you sure you want to delete "${deleteConfirm?.file_name}"? This action cannot be undone.`}
        confirmText="Delete"
        type="danger"
      />
    </div>
  );
};

export default Manuscripts;
