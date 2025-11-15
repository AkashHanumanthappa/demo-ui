import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export const Navigation = () => {
  const { user, logout, getUserDisplayName, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="bg-primary-600 text-white shadow-soft">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link to="/dashboard" className="text-xl font-bold hover:text-primary-100 transition">
              Manuscript Processor
            </Link>
            <div className="hidden md:flex space-x-1">
              <Link
                to="/dashboard"
                className="px-3 py-2 rounded-md hover:bg-primary-700 transition"
              >
                Dashboard
              </Link>
              <Link
                to="/manuscripts"
                className="px-3 py-2 rounded-md hover:bg-primary-700 transition"
              >
                Manuscripts
              </Link>
              <Link
                to="/profile"
                className="px-3 py-2 rounded-md hover:bg-primary-700 transition"
              >
                Profile
              </Link>
              <Link
                to="/settings"
                className="px-3 py-2 rounded-md hover:bg-primary-700 transition"
              >
                Settings
              </Link>
              {isAdmin() && (
                <Link
                  to="/admin"
                  className="px-3 py-2 rounded-md hover:bg-primary-700 transition"
                >
                  Admin
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium">{getUserDisplayName()}</span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-primary-700 rounded-md hover:bg-primary-800 transition font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
