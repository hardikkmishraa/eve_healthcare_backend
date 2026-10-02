import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { formatDateTime } from '../utils/formatters';
import { Mail, Phone, Shield, Calendar, LogOut } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold text-slate-900">Patient Profile</h1>
        <p className="mt-1 text-sm text-slate-600">
          Your personal details and account credentials.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-4 border-b border-slate-100 pb-5">
          <div className="w-14 h-14 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xl border border-blue-100">
            {user.full_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">{user.full_name}</h2>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700">
              Role: {user.role}
            </span>
          </div>
        </div>

        <div className="space-y-4 text-sm">
          <div className="flex items-center gap-3 text-slate-700">
            <Mail className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-slate-500 w-28">Email:</span>
            <span className="font-medium text-slate-900">{user.email}</span>
          </div>

          <div className="flex items-center gap-3 text-slate-700">
            <Phone className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-slate-500 w-28">Phone:</span>
            <span className="font-medium text-slate-900">
              {user.phone_number || 'Not provided'}
            </span>
          </div>

          <div className="flex items-center gap-3 text-slate-700">
            <Shield className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-slate-500 w-28">Account ID:</span>
            <span className="font-mono text-xs text-slate-600">{user.id}</span>
          </div>

          <div className="flex items-center gap-3 text-slate-700">
            <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="text-slate-500 w-28">Member Since:</span>
            <span className="font-medium text-slate-900">
              {formatDateTime(user.created_at)}
            </span>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-100">
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 px-4 py-2 border border-rose-200 text-rose-700 hover:bg-rose-50 rounded-md text-sm font-medium transition-colors"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </div>
    </div>
  );
};
