import { useState, useEffect } from 'react';
import { getAllFiles, getAllUsers } from '../../utils/api';
import { useNotification } from '../../contexts/NotificationContext';
import Navigation from '../../components/shared/Navigation';
import Loading from '../../components/shared/Loading';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const ActivityLogs = () => {
  const { handleError } = useNotification();
  const [activities, setActivities] = useState([]);
  const [users, setUsers] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    loadActivityData();
  }, []);

  const loadActivityData = async () => {
    try {
      setLoading(true);
      const [filesResponse, usersResponse] = await Promise.all([
        getAllFiles(),
        getAllUsers()
      ]);
      
      const files = filesResponse.data?.files || [];
      const usersData = usersResponse.data?.users || [];

      const sortedFiles = files.sort((a, b) => 
        new Date(b.created_at) - new Date(a.created_at)
      );

      setActivities(sortedFiles);
      setUsers(usersData);

      const monthlyStats = calculateMonthlyData(files);
      setMonthlyData(monthlyStats);

    } catch (error) {
      handleError(error, 'Failed to load activity logs');
    } finally {
      setLoading(false);
    }
  };

  const getUserName = (userId) => {
    const cleaned = String(userId?._id || userId);
    const user = users.find(u => String(u._id) === cleaned);
    return user ? user.username : "Unknown";
  };

  const calculateMonthlyData = (files) => {
    const monthMap = new Map();
    
    const completedFiles = files.filter(f => f.status === 'completed' && (f.updated_at || f.updatedAt || f.created_at || f.createdAt));
    
    const completedDates = completedFiles
      .map(f => {
        const dateStr = f.updated_at || f.updatedAt || f.created_at || f.createdAt;
        return new Date(dateStr);
      })
      .filter(d => !isNaN(d.getTime()));
    
    const now = new Date();
    let startDate, endDate;
    
    if (completedDates.length > 0) {
      const minDate = new Date(Math.min(...completedDates.map(d => d.getTime())));
      const maxDate = new Date(Math.max(...completedDates.map(d => d.getTime())));
      startDate = new Date(Math.min(minDate.getTime(), new Date(now.getFullYear(), now.getMonth() - 11, 1).getTime()));
      endDate = new Date(Math.max(maxDate.getTime(), now.getTime()));
    } else {
      startDate = new Date(now.getFullYear(), now.getMonth() - 11, 1);
      endDate = now;
    }
    
    const currentMonth = new Date(startDate.getFullYear(), startDate.getMonth(), 1);
    const lastMonth = new Date(endDate.getFullYear(), endDate.getMonth(), 1);
    
    while (currentMonth <= lastMonth) {
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth() + 1;
      const monthKey = `${year}-${String(month).padStart(2, '0')}`;
      const monthLabel = currentMonth.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      
      monthMap.set(monthKey, {
        month: monthLabel,
        conversions: 0,
        timestamp: currentMonth.getTime()
      });
      
      currentMonth.setMonth(currentMonth.getMonth() + 1);
    }
    
    completedFiles.forEach(file => {
      const dateStr = file.updated_at || file.updatedAt || file.created_at || file.createdAt;
      if (!dateStr) return;
      
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return;
      
      const year = date.getFullYear();
      const month = date.getMonth() + 1;
      const monthKey = `${year}-${String(month).padStart(2, '0')}`;
      
      if (monthMap.has(monthKey)) {
        const monthData = monthMap.get(monthKey);
        monthData.conversions++;
      }
    });

    const result = Array.from(monthMap.values());
    return result.slice(-24);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'N/A';
    
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      uploaded: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Uploaded' },
      processing: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Processing' },
      completed: { bg: 'bg-green-100', text: 'text-green-800', label: 'Completed' },
      failed: { bg: 'bg-red-100', text: 'text-red-800', label: 'Failed' }
    };
    
    const config = statusConfig[status] || statusConfig.uploaded;
    
    return (
      <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const filteredActivities = activities.filter(activity => {
    if (filter === 'all') return true;
    return activity.status === filter;
  });

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white px-4 py-3 border-2 rounded-lg shadow-xl" style={{ borderColor: '#6890b8' }}>
          <p className="text-sm font-semibold" style={{ color: '#2c3e50' }}>{payload[0].payload.month}</p>
          <p className="text-sm font-medium" style={{ color: '#4f7299' }}>
            {payload[0].value} {payload[0].value === 1 ? 'conversion' : 'conversions'}
          </p>
        </div>
      );
    }
    return null;
  };

  const stats = {
    total: activities.length,
    completed: activities.filter(a => a.status === 'completed').length,
    failed: activities.filter(a => a.status === 'failed').length,
    processing: activities.filter(a => a.status === 'processing' || a.status === 'uploaded').length
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#f0f4f8' }}>
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2" style={{ color: '#2c3e50' }}>
            Activity Logs
          </h1>
          <p style={{ color: '#6890b8' }} className="font-medium">Monitor file conversions and system activity</p>
        </div>

        {loading ? (
          <div className="py-20">
            <Loading />
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #6890b8' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Total Activities</p>
                    <p className="text-3xl font-bold" style={{ color: '#6890b8' }}>{stats.total}</p>
                  </div>
                  <div className="rounded-full p-3" style={{ backgroundColor: '#e8f3f9' }}>
                    <svg className="w-8 h-8" style={{ color: '#6890b8' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #10b981' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Completed</p>
                    <p className="text-3xl font-bold text-green-600">{stats.completed}</p>
                  </div>
                  <div className="bg-green-100 rounded-full p-3">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #3b82f6' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Processing</p>
                    <p className="text-3xl font-bold text-blue-600">{stats.processing}</p>
                  </div>
                  <div className="bg-blue-100 rounded-full p-3">
                    <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #ef4444' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Failed</p>
                    <p className="text-3xl font-bold text-red-600">{stats.failed}</p>
                  </div>
                  <div className="bg-red-100 rounded-full p-3">
                    <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
              <h2 className="text-xl font-bold mb-6 flex items-center" style={{ color: '#2c3e50' }}>
                <span className="rounded-lg p-2 mr-3" style={{ backgroundColor: '#e8f3f9' }}>
                  <svg className="w-5 h-5" style={{ color: '#4f7299' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                  </svg>
                </span>
                Files Converted Per Month
              </h2>
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={monthlyData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorConversionsActivity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6890b8" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#6890b8" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="month" 
                    stroke="#6b7280"
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis 
                    stroke="#6b7280"
                    style={{ fontSize: '12px' }}
                    allowDecimals={false}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} iconType="rect" />
                  <Area 
                    type="monotone" 
                    dataKey="conversions" 
                    stroke="#6890b8" 
                    strokeWidth={3}
                    fill="url(#colorConversionsActivity)"
                    fillOpacity={1}
                    name="Conversions"
                    dot={{ fill: '#6890b8', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold" style={{ color: '#2c3e50' }}>Recent Activities</h2>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => setFilter('all')} 
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        filter === 'all' 
                          ? 'text-white shadow-md' 
                          : 'bg-gray-100 hover:bg-gray-200'
                      }`}
                      style={filter === 'all' ? { 
                        background: 'linear-gradient(135deg, #6890b8 0%, #5882ab 100%)',
                        border: '2px solid #3d5b7a'
                      } : { color: '#4b5563' }}
                    >
                      All
                    </button>
                    <button onClick={() => setFilter('completed')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'completed' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>Completed</button>
                    <button onClick={() => setFilter('processing')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'processing' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>Processing</button>
                    <button onClick={() => setFilter('failed')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'failed' ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>Failed</button>
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">File Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Upload Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Updated</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredActivities.map((activity) => (
                      <tr key={activity.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <svg className="w-5 h-5 text-gray-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <div>
                              <div className="text-sm font-medium text-gray-900">{activity.original_filename || activity.originalName}</div>
                              {(activity.file_size || activity.fileSize) && <div className="text-xs text-gray-500">{((activity.file_size || activity.fileSize) / 1024 / 1024).toFixed(2)} MB</div>}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{getUserName(activity.user_id || activity.uploadedBy)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(activity.status)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(activity.created_at || activity.createdAt)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(activity.updated_at || activity.updatedAt)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {filteredActivities.length === 0 && (
                  <div className="text-center py-12">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No activities found</h3>
                    <p className="mt-1 text-sm text-gray-500">{filter === 'all' ? 'No activities to display yet.' : `No ${filter} activities found.`}</p>
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

export default ActivityLogs;