'use client';
import React, { useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { useAuth } from '@/contexts/AuthContext';
import { Settings, User, Key, Shield } from 'lucide-react';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const [name, setName] = useState(user?.full_name || '');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your account and preferences</p>
        </div>

        {/* Profile */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <User className="w-5 h-5 text-purple-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Profile</h2>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Full Name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
              <input type="email" value={user?.email || ''} disabled
                className="w-full px-4 py-2.5 bg-gray-100 border border-gray-200 rounded-xl text-sm text-gray-500" />
            </div>
            <button onClick={handleSave}
              className="px-5 py-2.5 bg-purple-600 text-white rounded-xl text-sm font-medium hover:bg-purple-700">
              {saved ? '✓ Saved' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* API Key Info */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
              <Key className="w-5 h-5 text-amber-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">API Configuration</h2>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            AI features require a Google Gemini API key. Add it to the <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">.env</code> file on the server.
          </p>
          <div className="bg-gray-50 rounded-xl p-4 font-mono text-xs text-gray-600">
            GEMINI_API_KEY=your-api-key-here
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Get your API key from <a href="https://makersuite.google.com/app/apikey" target="_blank" className="text-purple-600 underline">Google AI Studio</a>
          </p>
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-2xl border border-red-100 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-red-100 rounded-xl flex items-center justify-center">
              <Shield className="w-5 h-5 text-red-600" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Account</h2>
          </div>
          <button onClick={logout} className="px-5 py-2.5 border border-red-200 text-red-600 rounded-xl text-sm font-medium hover:bg-red-50">
            Sign Out
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
