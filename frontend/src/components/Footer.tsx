import React from 'react';
import { Activity } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2 text-slate-700 font-semibold text-sm">
            <Activity className="w-4 h-4 text-blue-600" />
            <span>EVE Healthcare Diagnostic Services</span>
          </div>
          <p className="text-sm text-slate-500 text-center">
            Reliable diagnostic test booking, centre discovery, and simulated payment engine.
          </p>
          <div className="text-xs text-slate-400">
            © {new Date().getFullYear()} EVE Healthcare. All rights reserved.
          </div>
        </div>
      </div>
    </footer>
  );
};
