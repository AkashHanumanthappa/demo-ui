import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useManuscripts } from '../hooks/useManuscripts';
import { useNotification } from '../contexts/NotificationContext';
import Navigation from '../components/shared/Navigation';
import Loading from '../components/shared/Loading';

export const Dashboard = () => {
  const { user, getUserDisplayName } = useAuth();
  const { manuscripts, loading, getManuscripts, getStatistics } = useManuscripts();
  const { handleError } = useNotification();
  const [stats, setStats] = useState({
    total: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      await getManuscripts({ limit: 5 });
      const statsData = await getStatistics();
      setStats(statsData);
    } catch (error) {
      handleError(error, 'Failed to load dashboard data');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      complete: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-secondary-50">
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900">
            Welcome, {getUserDisplayName()}!
          </h1>
          <p className="mt-2 text-secondary-600">
            Here's an overview of your manuscript processing activity
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="card p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-primary-500 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-secondary-600">Total Manuscripts</p>
                <p className="text-2xl font-semibold text-secondary-900">{stats.total}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-blue-500 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-secondary-600">Processing</p>
                <p className="text-2xl font-semibold text-secondary-900">{stats.processing}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-green-500 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-secondary-600">Completed</p>
                <p className="text-2xl font-semibold text-secondary-900">{stats.completed}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-red-500 rounded-md p-3">
                <svg
                  className="h-6 w-6 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div className="ml-5">
                <p className="text-sm font-medium text-secondary-600">Failed</p>
                <p className="text-2xl font-semibold text-secondary-900">{stats.failed}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="px-6 py-4 border-b border-secondary-200">
            <h2 className="text-xl font-semibold text-secondary-900">Recent Manuscripts</h2>
          </div>
          <div className="px-6 py-4">
            {loading ? (
              <Loading />
            ) : manuscripts.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-secondary-500">No manuscripts yet</p>
                <Link
                  to="/manuscripts"
                  className="mt-4 inline-block btn-primary"
                >
                  Upload Your First Manuscript
                </Link>
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
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-secondary-200">
                    {manuscripts.map((manuscript) => (
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
                          {new Date(manuscript.upload_date).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <div className="px-6 py-4 border-t border-secondary-200 bg-secondary-50">
            <Link
              to="/manuscripts"
              className="text-primary-600 hover:text-primary-700 font-medium transition"
            >
              View All Manuscripts →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
