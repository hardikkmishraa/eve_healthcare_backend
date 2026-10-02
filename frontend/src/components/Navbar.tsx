import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Menu, X, Activity, User as UserIcon } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
    setMobileMenuOpen(false);
  };

  const isActive = (path: string) => location.pathname === path;

  const navLinkClass = (path: string) =>
    `px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
      isActive(path)
        ? 'text-blue-600 bg-blue-50'
        : 'text-slate-600 hover:text-blue-600 hover:bg-slate-50'
    }`;

  const mobileNavLinkClass = (path: string) =>
    `block px-3 py-2 text-base font-medium rounded-md ${
      isActive(path)
        ? 'text-blue-600 bg-blue-50'
        : 'text-slate-700 hover:text-blue-600 hover:bg-slate-50'
    }`;

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Brand Logo */}
          <Link
            to="/"
            className="flex items-center gap-2 text-blue-600 font-bold text-lg tracking-tight"
          >
            <Activity className="w-5 h-5 text-blue-600" />
            <span>EVE Healthcare</span>
          </Link>

          {/* Desktop Navigation Links */}
          <div className="hidden md:flex items-center gap-1">
            <Link to="/centres" className={navLinkClass('/centres')}>
              Centres
            </Link>
            <Link to="/tests" className={navLinkClass('/tests')}>
              Tests
            </Link>
            {user && (
              <Link to="/bookings" className={navLinkClass('/bookings')}>
                My Bookings
              </Link>
            )}
          </div>

          {/* Right Action / Auth Buttons */}
          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <Link
                  to="/profile"
                  className="flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-blue-600 px-3 py-1.5 rounded-md hover:bg-slate-50"
                >
                  <UserIcon className="w-4 h-4 text-slate-500" />
                  <span>{user.full_name}</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="text-sm font-medium text-slate-600 hover:text-red-600 px-3 py-1.5 rounded-md border border-slate-200 hover:border-red-200 transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="text-sm font-medium text-slate-700 hover:text-blue-600 px-3 py-1.5 rounded-md hover:bg-slate-50"
                >
                  Login
                </Link>
                <Link
                  to="/signup"
                  className="text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 px-4 py-1.5 rounded-md shadow-sm transition-colors"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="text-slate-600 hover:text-slate-900 p-2 rounded-md"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 px-4 pt-2 pb-4 space-y-1 bg-white">
          <Link
            to="/centres"
            className={mobileNavLinkClass('/centres')}
            onClick={() => setMobileMenuOpen(false)}
          >
            Centres
          </Link>
          <Link
            to="/tests"
            className={mobileNavLinkClass('/tests')}
            onClick={() => setMobileMenuOpen(false)}
          >
            Tests
          </Link>
          {user && (
            <Link
              to="/bookings"
              className={mobileNavLinkClass('/bookings')}
              onClick={() => setMobileMenuOpen(false)}
            >
              My Bookings
            </Link>
          )}

          <div className="pt-3 border-t border-slate-100">
            {user ? (
              <div className="space-y-2">
                <Link
                  to="/profile"
                  className={mobileNavLinkClass('/profile')}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Profile ({user.full_name})
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-base font-medium text-red-600 hover:bg-red-50 rounded-md"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="space-y-2 pt-1">
                <Link
                  to="/login"
                  className={mobileNavLinkClass('/login')}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Login
                </Link>
                <Link
                  to="/signup"
                  className="block text-center px-3 py-2 text-base font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};
