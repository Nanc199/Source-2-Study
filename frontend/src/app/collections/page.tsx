'use client';
import React, { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi } from '@/lib/api';
import Link from 'next/link';
import { FolderOpen, Plus, Search, FileText, X } from 'lucide-react';

export default function CollectionsPage() {
  const [collections, setCollections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState('');

  const load = () => {
    collectionsApi.list().then(setCollections).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await collectionsApi.create({ name: name.trim(), description: desc.trim() || undefined });
      setShowModal(false);
      setName('');
      setDesc('');
      load();
    } catch (err) {
      alert('Failed to create collection');
    } finally {
      setCreating(false);
    }
  };

  const filtered = collections.filter((c: any) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Collections</h1>
          <p className="text-gray-500 text-sm mt-1">Organize your study materials into collections</p>
        </div>
        <button onClick={() => setShowModal(true)} className="inline-flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-medium px-5 py-2.5 rounded-xl hover:from-purple-700 hover:to-indigo-700 shadow-lg shadow-purple-200 text-sm">
          <Plus className="w-4 h-4" /> New Collection
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search collections..."
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full border-4 border-gray-200 border-t-purple-600 h-10 w-10" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20">
          <FolderOpen className="w-16 h-16 mx-auto text-gray-200 mb-4" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No collections yet</h3>
          <p className="text-gray-400 text-sm mb-6">Create your first collection to start uploading study materials</p>
          <button onClick={() => setShowModal(true)} className="inline-flex items-center gap-2 bg-purple-600 text-white px-6 py-2.5 rounded-xl text-sm font-medium">
            <Plus className="w-4 h-4" /> Create Collection
          </button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((c: any) => (
            <Link key={c.id} href={`/collections/${c.id}`} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-lg hover:border-purple-100 transition-all group">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-11 h-11 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-xl flex items-center justify-center group-hover:from-purple-100 group-hover:to-indigo-100 transition-colors">
                  <FolderOpen className="w-5 h-5 text-purple-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">{c.name}</h3>
                  {c.description && <p className="text-xs text-gray-400 mt-0.5 truncate">{c.description}</p>}
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span className="flex items-center gap-1"><FileText className="w-3 h-3" /> {c.source_count || 0} sources</span>
                <span>{new Date(c.created_at).toLocaleDateString()}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">Create Collection</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Collection Name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} required
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="e.g., Artificial Intelligence" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Description (optional)</label>
                <textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={3}
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                  placeholder="What's this collection about?" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={creating} className="flex-1 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-medium disabled:opacity-50">
                  {creating ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
