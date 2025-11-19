import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAllUsers, getAllFiles } from '../../utils/api';
import { useNotification } from '../../contexts/NotificationContext';
import Navigation from '../../components/shared/Navigation';
import Loading from '../../components/shared/Loading';
import { AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const AdminDashboard = () => {
  const { handleError } = useNotification();
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    adminUsers: 0,
    totalFiles: 0,
    totalConversions: 0,
    successfulConversions: 0,
    failedConversions: 0,
    processingFiles: 0,
    pdfConversions: 0,
    epubConversions: 0
  });
  const [monthlyData, setMonthlyData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const calculateMonthlyData = (files) => {
    const monthMap = new Map();
    
    const completedFiles = files.filter(f => f.status === 'completed' && (f.updated_at || f.updatedAt || f.created_at || f.createdAt || f.uploadDate));
    
    const completedDates = completedFiles
      .map(f => {
        const dateStr = f.updated_at || f.updatedAt || f.created_at || f.createdAt || f.uploadDate;
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
      const dateStr = file.updated_at || file.updatedAt || file.created_at || file.createdAt || file.uploadDate;
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

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      const [usersResponse, filesResponse] = await Promise.all([
        getAllUsers(),
        getAllFiles()
      ]);

      const users = usersResponse.data?.users || [];
      const files = filesResponse.data?.files || [];

      const totalUsers = users.length;
      const adminUsers = users.filter(u => u.role === 'admin').length;
      const activeUsers = users.filter(u => {
        return files.some(f => f.user_id === u.id);
      }).length;

      const totalFiles = files.length;
      const completedFiles = files.filter(f => f.status === 'completed');
      const failedFiles = files.filter(f => f.status === 'failed');
      const processingFiles = files.filter(f => f.status === 'processing' || f.status === 'uploaded');

      let pdfCount = 0;
      let epubCount = 0;

      completedFiles.forEach(file => {
        if (file.output_files && Array.isArray(file.output_files)) {
          file.output_files.forEach(outputFile => {
            const fileName = outputFile.toLowerCase();
            if (fileName.endsWith('.pdf')) {
              pdfCount++;
            } else if (fileName.endsWith('.epub')) {
              epubCount++;
            }
          });
        }
      });

      const monthlyStats = calculateMonthlyData(files);
      setMonthlyData(monthlyStats);

      setStats({
        totalUsers,
        activeUsers,
        adminUsers,
        totalFiles,
        totalConversions: completedFiles.length + failedFiles.length,
        successfulConversions: completedFiles.length,
        failedConversions: failedFiles.length,
        processingFiles: processingFiles.length,
        pdfConversions: pdfCount,
        epubConversions: epubCount
      });

    } catch (error) {
      handleError(error, 'Failed to load dashboard statistics');
    } finally {
      setLoading(false);
    }
  };

  const conversionStatusData = [
    { name: 'Successful', value: stats.successfulConversions, color: '#10b981' },
    { name: 'Failed', value: stats.failedConversions, color: '#ef4444' },
    { name: 'Processing', value: stats.processingFiles, color: '#f59e0b' }
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white px-4 py-3 border-2 rounded-lg shadow-xl" style={{ borderColor: '#6890b8' }}>
          <p className="text-sm font-semibold" style={{ color: '#2c3e50' }}>{payload[0].payload.month || payload[0].name}</p>
          <p className="text-sm font-medium" style={{ color: '#4f7299' }}>
            {payload[0].value} {payload[0].value === 1 ? 'conversion' : 'conversions'}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#f0f4f8' }}>
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2" style={{ color: '#2c3e50' }}>
            Admin Dashboard
          </h1>
          <p style={{ color: '#6890b8' }} className="font-medium">R2 Digital Library Management System</p>
        </div>

        {loading ? (
          <div className="py-20">
            <Loading />
          </div>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #6890b8' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Total Users</p>
                    <p className="text-3xl font-bold" style={{ color: '#6890b8' }}>{stats.totalUsers}</p>
                    <p className="text-xs mt-1" style={{ color: '#9ca3af' }}>
                      {stats.adminUsers} admin{stats.adminUsers !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <div className="rounded-full p-3" style={{ backgroundColor: '#e8f3f9' }}>
                    <svg className="w-8 h-8" style={{ color: '#6890b8' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #4f7299' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Active Users</p>
                    <p className="text-3xl font-bold" style={{ color: '#4f7299' }}>{stats.activeUsers}</p>
                    <p className="text-xs mt-1" style={{ color: '#9ca3af' }}>
                      {stats.totalUsers > 0 ? Math.round((stats.activeUsers / stats.totalUsers) * 100) : 0}% of total
                    </p>
                  </div>
                  <div className="rounded-full p-3" style={{ backgroundColor: '#e8f3f9' }}>
                    <svg className="w-8 h-8" style={{ color: '#4f7299' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #10b981' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Total Files</p>
                    <p className="text-3xl font-bold text-green-600">{stats.totalFiles}</p>
                    <p className="text-xs mt-1" style={{ color: '#9ca3af' }}>
                      {stats.processingFiles} processing
                    </p>
                  </div>
                  <div className="bg-green-50 rounded-full p-3">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow" style={{ borderLeft: '4px solid #3d5b7a' }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Total Conversions</p>
                    <p className="text-3xl font-bold" style={{ color: '#3d5b7a' }}>{stats.totalConversions}</p>
                    <p className="text-xs mt-1" style={{ color: '#9ca3af' }}>
                      {stats.successfulConversions} successful
                    </p>
                  </div>
                  <div className="rounded-full p-3" style={{ backgroundColor: '#e8f3f9' }}>
                    <svg className="w-8 h-8" style={{ color: '#3d5b7a' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <Link
                to="/admin/users"
                className="text-white rounded-xl shadow-lg p-6 hover:shadow-xl hover:scale-105 transition-all"
                style={{
                  background: 'linear-gradient(135deg, #6890b8 0%, #5882ab 100%)',
                  border: '2px solid #3d5b7a'
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">User Management</h3>
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </div>
                <p className="text-blue-100 text-sm">Manage users and permissions</p>
              </Link>

              <Link
                to="/admin/activities"
                className="text-white rounded-xl shadow-lg p-6 hover:shadow-xl hover:scale-105 transition-all"
                style={{
                  background: 'linear-gradient(135deg, #4f7299 0%, #3d5b7a 100%)',
                  border: '2px solid #2c4356'
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">Activity Logs</h3>
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </div>
                <p className="opacity-90 text-sm">View system activity logs</p>
              </Link>

              <Link
                to="/admin/reports"
                className="text-white rounded-xl shadow-lg p-6 hover:shadow-xl hover:scale-105 transition-all"
                style={{
                  background: 'linear-gradient(135deg, #5882ab 0%, #4f7299 100%)',
                  border: '2px solid #3d5b7a'
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">Reports</h3>
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                </div>
                <p className="opacity-90 text-sm">Generate detailed reports</p>
              </Link>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Conversion Status Chart */}
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-xl font-bold mb-6 flex items-center" style={{ color: '#2c3e50' }}>
                  <span className="rounded-lg p-2 mr-3" style={{ backgroundColor: '#e8f3f9' }}>
                    <svg className="w-5 h-5" style={{ color: '#6890b8' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </span>
                  Conversion Status
                </h2>
                {stats.totalConversions > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <PieChart>
                      <Pie
                        data={conversionStatusData.filter(item => item.value > 0)}
                        cx="50%"
                        cy="50%"
                        labelLine={true}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={110}
                        fill="#8884d8"
                        dataKey="value"
                        paddingAngle={2}
                      >
                        {conversionStatusData.filter(item => item.value > 0).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend 
                        verticalAlign="bottom" 
                        height={36}
                        iconType="circle"
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-400">
                    <div className="text-center">
                      <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                      <p className="text-sm">No conversion data available</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Format Conversion Chart */}
              <div className="bg-white rounded-xl shadow-lg p-6">
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
                      <linearGradient id="colorConversions" x1="0" y1="0" x2="0" y2="1">
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
                    <Legend 
                      wrapperStyle={{ paddingTop: '20px' }}
                      iconType="rect"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="conversions" 
                      stroke="#6890b8" 
                      strokeWidth={3}
                      fill="url(#colorConversions)"
                      fillOpacity={1}
                      name="Conversions"
                      dot={{ fill: '#6890b8', strokeWidth: 2, r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Detailed Statistics */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-xl font-bold mb-6 flex items-center" style={{ color: '#2c3e50' }}>
                  <span className="rounded-lg p-2 mr-3" style={{ backgroundColor: '#e8f3f9' }}>
                    <svg className="w-5 h-5" style={{ color: '#6890b8' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  </span>
                  User Statistics
                </h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Total Users</span>
                    <span className="text-2xl font-bold" style={{ color: '#2c3e50' }}>{stats.totalUsers}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg" style={{ backgroundColor: '#e8f3f9' }}>
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Active Users</span>
                    <span className="text-2xl font-bold" style={{ color: '#4f7299' }}>{stats.activeUsers}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg" style={{ backgroundColor: '#e8f3f9' }}>
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Admin Users</span>
                    <span className="text-2xl font-bold" style={{ color: '#6890b8' }}>{stats.adminUsers}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Regular Users</span>
                    <span className="text-2xl font-bold" style={{ color: '#2c3e50' }}>{stats.totalUsers - stats.adminUsers}</span>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-xl font-bold mb-6 flex items-center" style={{ color: '#2c3e50' }}>
                  <span className="rounded-lg p-2 mr-3" style={{ backgroundColor: '#e8f3f9' }}>
                    <svg className="w-5 h-5" style={{ color: '#4f7299' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                  </span>
                  Conversion Statistics
                </h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Total Conversions</span>
                    <span className="text-2xl font-bold" style={{ color: '#2c3e50' }}>{stats.totalConversions}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Successful</span>
                    <span className="text-2xl font-bold text-green-600">{stats.successfulConversions}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Failed</span>
                    <span className="text-2xl font-bold text-red-600">{stats.failedConversions}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                    <span className="font-medium" style={{ color: '#2c3e50' }}>Processing</span>
                    <span className="text-2xl font-bold text-yellow-600">{stats.processingFiles}</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;