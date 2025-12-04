import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useManuscripts } from '../hooks/useManuscripts';
import { useNotification } from '../contexts/NotificationContext';
import Navigation from '../components/shared/Navigation';
import Loading from '../components/shared/Loading';

export const Dashboard = () => {
  const { user, getUserDisplayName } = useAuth();
  const { manuscripts, loading, getManuscripts } = useManuscripts();
  const { handleError } = useNotification();
  const [stats, setStats] = useState({
    total: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  });
  
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    if (!hasLoadedRef.current) {
      hasLoadedRef.current = true;
      loadData();
    }
  }, []);

  // Calculate stats whenever manuscripts change
  useEffect(() => {
    if (Array.isArray(manuscripts)) {
      calculateStats(manuscripts);
    }
  }, [manuscripts]);

  const loadData = async () => {
    try {
      // Load all manuscripts (not just 5) to get accurate stats
      await getManuscripts({ limit: 100 });
    } catch (error) {
      handleError(error, 'Failed to load dashboard data');
    }
  };

  const calculateStats = (manuscriptsList) => {
    const statistics = {
      total: manuscriptsList.length,
      processing: manuscriptsList.filter(m => 
        m.status === 'processing' || m.status === 'uploaded' || m.status === 'pending'
      ).length,
      completed: manuscriptsList.filter(m => 
        m.status === 'completed' || m.status === 'complete'
      ).length,
      failed: manuscriptsList.filter(m => 
        m.status === 'failed'
      ).length,
    };
    
    setStats(statistics);
  };

  const getStatusColor = (status) => {
    const colors = {
      uploaded: 'bg-yellow-100 text-yellow-800',
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      complete: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getStatusLabel = (status) => {
    const labels = {
      uploaded: 'Processing',
      pending: 'Pending',
      processing: 'Processing',
      completed: 'Completed',
      complete: 'Completed',
      failed: 'Failed',
    };
    return labels[status] || status;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'N/A';
    
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Get only the 5 most recent manuscripts for display
  const recentManuscripts = Array.isArray(manuscripts) 
    ? manuscripts.slice(0, 5) 
    : [];

  const StatCard = ({ icon, title, value, color, borderColor }) => (
    <div 
      className="bg-white rounded-lg sm:rounded-xl shadow-md sm:shadow-lg p-4 sm:p-6 hover:shadow-xl transition-shadow"
      style={{ borderLeft: `4px solid ${borderColor}` }}
    >
      <div className="flex items-center">
        <div 
          className="flex-shrink-0 rounded-md p-2 sm:p-3"
          style={{ backgroundColor: color }}
        >
          {icon}
        </div>
        <div className="ml-3 sm:ml-5">
          <p className="text-xs sm:text-sm font-medium text-gray-600">{title}</p>
          <p className="text-xl sm:text-2xl font-semibold" style={{ color: color === '#6890b8' ? '#2c3e50' : color }}>
            {value}
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(to bottom right, #e8f0f8, #f5f9fc)' }}>
      <Navigation />
      <div className="w-full max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-4 sm:py-6 md:py-8">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold" style={{ color: '#2c3e50' }}>
            Welcome, {getUserDisplayName()}!
          </h1>
          <p className="mt-1 sm:mt-2 text-sm sm:text-base" style={{ color: '#6890b8' }}>
            Here's an overview of your manuscript processing activity
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 md:gap-6 mb-6 sm:mb-8">
          <StatCard
            icon={
              <svg className="h-5 w-5 sm:h-6 sm:w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
            title="Total"
            value={stats.total}
            color="#6890b8"
            borderColor="#6890b8"
          />
          
          <StatCard
            icon={
              <svg className="h-5 w-5 sm:h-6 sm:w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            }
            title="Processing"
            value={stats.processing}
            color="#3b82f6"
            borderColor="#3b82f6"
          />
          
          <StatCard
            icon={
              <svg className="h-5 w-5 sm:h-6 sm:w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            title="Completed"
            value={stats.completed}
            color="#10b981"
            borderColor="#10b981"
          />
          
          <StatCard
            icon={
              <svg className="h-5 w-5 sm:h-6 sm:w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            title="Failed"
            value={stats.failed}
            color="#ef4444"
            borderColor="#ef4444"
          />
        </div>

        {/* Recent Manuscripts Table */}
        <div className="bg-white rounded-lg sm:rounded-xl shadow-md sm:shadow-lg overflow-hidden">
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200">
            <h2 className="text-lg sm:text-xl font-semibold" style={{ color: '#2c3e50' }}>
              Recent Manuscripts
            </h2>
          </div>
          <div className="px-3 sm:px-6 py-3 sm:py-4">
            {loading ? (
              <Loading />
            ) : recentManuscripts.length === 0 ? (
              <div className="text-center py-6 sm:py-8">
                <svg className="mx-auto h-10 w-10 sm:h-12 sm:w-12 text-gray-400 mb-3 sm:mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm sm:text-base text-gray-500 mb-3 sm:mb-4">No manuscripts yet</p>
                <Link
                  to="/manuscripts"
                  className="inline-block px-4 sm:px-6 py-2 sm:py-3 text-sm sm:text-base text-white rounded-lg font-semibold shadow-lg hover:shadow-xl transition-all"
                  style={{ backgroundColor: '#4f7299' }}
                >
                  Upload Your First Manuscript
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto -mx-3 sm:mx-0">
                <div className="inline-block min-w-full align-middle">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 sm:px-6 py-2 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          File Name
                        </th>
                        <th className="px-3 sm:px-6 py-2 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="hidden sm:table-cell px-3 sm:px-6 py-2 sm:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Upload Date
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {recentManuscripts.map((manuscript) => {
                        const uniqueKey = manuscript.id || manuscript._id || `manuscript-${Math.random()}`;
                        return (
                          <tr key={uniqueKey} className="hover:bg-gray-50 transition">
                            <td className="px-3 sm:px-6 py-3 sm:py-4 text-xs sm:text-sm">
                              <div className="flex items-center">
                                <svg className="hidden sm:block w-5 h-5 text-gray-400 mr-2 sm:mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                <div className="min-w-0 flex-1">
                                  <span className="font-medium text-gray-900 break-words line-clamp-2">
                                    {manuscript.file_name || manuscript.original_filename || manuscript.originalName || 'Unnamed File'}
                                  </span>
                                  <div className="sm:hidden text-xs text-gray-500 mt-1">
                                    {formatDate(manuscript.upload_date || manuscript.created_at || manuscript.createdAt)}
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="px-3 sm:px-6 py-3 sm:py-4 whitespace-nowrap">
                              <span
                                className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(manuscript.status)}`}
                              >
                                {getStatusLabel(manuscript.status)}
                              </span>
                            </td>
                            <td className="hidden sm:table-cell px-3 sm:px-6 py-3 sm:py-4 whitespace-nowrap text-xs sm:text-sm text-gray-600">
                              {formatDate(manuscript.upload_date || manuscript.created_at || manuscript.createdAt)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
          {recentManuscripts.length > 0 && (
            <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-gray-200 bg-gray-50">
              <Link
                to="/manuscripts"
                className="text-sm sm:text-base font-medium transition hover:underline"
                style={{ color: '#4f7299' }}
              >
                View All Manuscripts →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;