import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { User, LogOut, Menu, X, BookOpen, Settings as SettingsIcon, Shield } from 'lucide-react';

export const Navigation = () => {
  const { user, logout, getUserDisplayName, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
    setMobileMenuOpen(false);
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  const mainNavLinks = [
    { path: '/dashboard', label: 'Browse', icon: BookOpen },
    { path: '/manuscripts', label: 'Manuscripts', icon: BookOpen },
    { path: '/profile', label: 'Profile', icon: User },
  ];

  const secondaryNavLinks = [
    { path: '/settings', label: 'Settings', icon: SettingsIcon },
  ];

  if (isAdmin()) {
    secondaryNavLinks.push({ path: '/admin', label: 'Admin', icon: Shield });
    secondaryNavLinks.push({ path: '/admin/users', label: 'Users', icon: User });
  }

  const handleNavClick = () => {
    setMobileMenuOpen(false);
  };

  return (
    <>
      {/* Top Bar with Logo and Menu Button */}
      <div className="bg-white" style={{ borderBottom: '2px solid #6890b8' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-3 sm:py-4">
            {/* Logo Section */}
            <Link to="/dashboard" className="flex items-center space-x-2 sm:space-x-3 hover:opacity-90 transition group">
              {/* Logo Icon */}
              <div className="relative">
                <div
                  className="w-10 h-10 sm:w-14 sm:h-14 rounded-full flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow"
                  style={{
                    background: 'linear-gradient(135deg, #6890b8 0%, #4f7299 100%)',
                    border: '2px solid #3d5b7a'
                  }}
                >
                  <svg className="w-6 h-6 sm:w-8 sm:h-8 text-white" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                    <path d="M8 12L11 15L16 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              {/* Logo Text */}
              <div>
                <h1 className="text-lg sm:text-2xl font-bold leading-tight" style={{ color: '#2c3e50' }}>
                  Manuscript <span style={{ color: '#4f7299' }}>Processor</span>
                </h1>
                <p className="text-xs font-medium hidden sm:block" style={{ color: '#6890b8' }}>Digital Library Management System</p>
              </div>
            </Link>

            <div className="flex items-center space-x-3 sm:space-x-4">
              {/* User Display - Desktop Only */}
              <div className="hidden lg:flex items-center space-x-3">
                <div className="text-right">
                  <div className="text-sm font-semibold" style={{ color: '#2c3e50' }}>Login:</div>
                </div>
                <div
                  className="flex items-center space-x-2 px-4 py-2 rounded-lg"
                  style={{
                    backgroundColor: '#e8f3f9',
                    border: '1px solid #6890b8'
                  }}
                >
                  <User size={18} style={{ color: '#4f7299' }} />
                  <span className="font-medium" style={{ color: '#2c3e50' }}>{getUserDisplayName()}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="px-5 py-2 rounded-md transition font-semibold shadow-sm hover:shadow-md"
                  style={{
                    backgroundColor: '#3d5b7a',
                    color: 'white',
                    border: '2px solid #2c4356'
                  }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#2c4356'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = '#3d5b7a'}
                >
                  Log Out
                </button>
              </div>

              {/* Mobile/Tablet Menu Button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="lg:hidden p-2 rounded-md transition"
                style={{
                  backgroundColor: mobileMenuOpen ? '#e8f3f9' : 'transparent',
                  border: '1px solid #6890b8'
                }}
                aria-label="Toggle menu"
              >
                {mobileMenuOpen ? <X size={24} style={{ color: '#4f7299' }} /> : <Menu size={24} style={{ color: '#4f7299' }} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Bar - Desktop Only */}
      <div
        className="hidden lg:block shadow-xl"
        style={{
          backgroundColor: '#6890b8',
          backgroundImage: 'linear-gradient(180deg, #8caed1 0%, #6890b8 50%, #5882ab 100%)',
          borderBottom: '3px solid #3d5b7a'
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-3 py-3">
            {/* Main Navigation Links */}
            {mainNavLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className="flex items-center space-x-2 px-6 py-2.5 rounded-md font-semibold transition-all text-white"
                  style={{
                    backgroundColor: isActive(link.path) ? '#5882ab' : '#5882ab',
                    border: '3px solid #3d5b7a',
                    boxShadow: isActive(link.path)
                      ? 'inset 0 3px 6px rgba(0,0,0,0.3), 0 2px 4px rgba(0,0,0,0.15)'
                      : 'inset 0 1px 3px rgba(255,255,255,0.15), 0 2px 4px rgba(0,0,0,0.1)',
                    opacity: isActive(link.path) ? '1' : '0.95'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive(link.path)) {
                      e.currentTarget.style.backgroundColor = '#6890b8';
                      e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(255,255,255,0.2), 0 3px 6px rgba(0,0,0,0.15)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive(link.path)) {
                      e.currentTarget.style.backgroundColor = '#5882ab';
                      e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(255,255,255,0.15), 0 2px 4px rgba(0,0,0,0.1)';
                    }
                  }}
                >
                  <Icon size={18} />
                  <span>{link.label}</span>
                </Link>
              );
            })}

            {/* Secondary Navigation Links */}
            {secondaryNavLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-md font-semibold transition-all text-white"
                  style={{
                    backgroundColor: isActive(link.path) ? '#5882ab' : '#5882ab',
                    border: '3px solid #3d5b7a',
                    boxShadow: isActive(link.path)
                      ? 'inset 0 3px 6px rgba(0,0,0,0.3), 0 2px 4px rgba(0,0,0,0.15)'
                      : 'inset 0 1px 3px rgba(255,255,255,0.15), 0 2px 4px rgba(0,0,0,0.1)',
                    opacity: isActive(link.path) ? '1' : '0.95'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive(link.path)) {
                      e.currentTarget.style.backgroundColor = '#6890b8';
                      e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(255,255,255,0.2), 0 3px 6px rgba(0,0,0,0.15)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive(link.path)) {
                      e.currentTarget.style.backgroundColor = '#5882ab';
                      e.currentTarget.style.boxShadow = 'inset 0 1px 3px rgba(255,255,255,0.15), 0 2px 4px rgba(0,0,0,0.1)';
                    }
                  }}
                >
                  <Icon size={18} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* Mobile/Tablet Menu Dropdown */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden shadow-xl animate-slide-in"
          style={{
            backgroundColor: 'white',
            borderBottom: '2px solid #6890b8',
            position: 'relative',
            zIndex: 50
          }}
        >
          <div className="px-4 py-4 space-y-2 max-h-screen overflow-y-auto">
            {/* User Section */}
            <div
              className="flex items-center space-x-3 px-4 py-3 rounded-lg mb-3"
              style={{
                backgroundColor: '#e8f3f9',
                border: '1px solid #6890b8'
              }}
            >
              <User size={20} style={{ color: '#4f7299' }} />
              <div>
                <div className="text-xs font-medium" style={{ color: '#6890b8' }}>Logged in as</div>
                <div className="font-semibold text-sm sm:text-base" style={{ color: '#2c3e50' }}>{getUserDisplayName()}</div>
              </div>
            </div>

            {/* Navigation Links */}
            <div className="space-y-1">
              <div className="text-xs font-semibold px-4 py-2" style={{ color: '#6890b8' }}>MAIN MENU</div>
              {mainNavLinks.map((link) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    onClick={handleNavClick}
                    className="flex items-center space-x-3 px-4 py-3 rounded-lg transition-all"
                    style={{
                      backgroundColor: isActive(link.path) ? '#e8f3f9' : 'transparent',
                      borderLeft: isActive(link.path) ? '4px solid #4f7299' : '4px solid transparent',
                      color: isActive(link.path) ? '#2c3e50' : '#6890b8',
                      fontWeight: isActive(link.path) ? '600' : '500'
                    }}
                  >
                    <Icon size={20} />
                    <span className="text-sm sm:text-base">{link.label}</span>
                  </Link>
                );
              })}
            </div>

            {/* Secondary Links */}
            {secondaryNavLinks.length > 0 && (
              <div className="space-y-1 pt-2 border-t" style={{ borderColor: '#e8f3f9' }}>
                <div className="text-xs font-semibold px-4 py-2" style={{ color: '#6890b8' }}>SETTINGS</div>
                {secondaryNavLinks.map((link) => {
                  const Icon = link.icon;
                  return (
                    <Link
                      key={link.path}
                      to={link.path}
                      onClick={handleNavClick}
                      className="flex items-center space-x-3 px-4 py-3 rounded-lg transition-all"
                      style={{
                        backgroundColor: isActive(link.path) ? '#e8f3f9' : 'transparent',
                        borderLeft: isActive(link.path) ? '4px solid #4f7299' : '4px solid transparent',
                        color: isActive(link.path) ? '#2c3e50' : '#6890b8',
                        fontWeight: isActive(link.path) ? '600' : '500'
                      }}
                    >
                      <Icon size={20} />
                      <span className="text-sm sm:text-base">{link.label}</span>
                    </Link>
                  );
                })}
              </div>
            )}

            {/* Logout Button */}
            <div className="pt-3">
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 rounded-lg transition font-semibold shadow-md text-sm sm:text-base"
                style={{
                  backgroundColor: '#3d5b7a',
                  color: 'white',
                  border: '2px solid #2c4356'
                }}
              >
                <LogOut size={18} />
                <span>Log Out</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Navigation;
