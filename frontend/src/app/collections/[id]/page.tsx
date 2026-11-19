'use client';
import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, sourcesApi } from '@/lib/api';
import {
  ArrowLeft, Upload, FileText, Globe, Youtube, Image, Trash2,
  CheckCircle2, XCircle, Loader2, RefreshCw, Plus, Link2
} from 'lucide-react';
import Link from 'next/link';

const typeIcons: Record<string, any> = {
  pdf: FileText, docx: FileText, pptx: FileText, image: Image, url: Globe, youtube: Youtube,
};
const typeColors: Record<string, string> = {
  pdf: 'text-red-500 bg-red-50', docx: 'text-blue-500 bg-blue-50', pptx: 'text-orange-500 bg-orange-50',
  image: 'text-green-500 bg-green-50', url: 'text-purple-500 bg-purple-50', youtube: 'text-rose-500 bg-rose-50',
};

export default function CollectionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);
  const [collection, setCollection] = useState<any>(null);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [ytInput, setYtInput] = useState('');
  const [showUrlForm, setShowUrlForm] = useState(false);
  const [showYtForm, setShowYtForm] = useState(false);
  const [tab, setTab] = useState<'sources' | 'actions'>('sources');

  const load = useCallback(() => {
    Promise.all([
      collectionsApi.get(id),
      sourcesApi.list(id),
    ]).then(([c, s]) => {
      setCollection(c);
      setSources(s || []);
    }).catch(() => router.push('/collections'))
      .finally(() => setLoading(false));
  }, [id, router]);

  useEffect(() => { load(); }, [load]);

  // Poll for processing status
  useEffect(() => {
    const processing = sources.some((s: any) => s.status === 'pending' || s.status === 'processing');
    if (!processing) return;
    const interval = setInterval(() => {
      sourcesApi.list(id).then(setSources).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [sources, id]);

  const handleFiles = async (files: FileList | File[]) => {
    if (!files.length) return;
    setUploading(true);
    try {
      await sourcesApi.upload(id, Array.from(files));
      setTimeout(load, 500);
    } catch (e: any) {
      alert(e.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const addUrl = async () => {
    if (!urlInput.trim()) return;
    try {
      await sourcesApi.addUrl(id, urlInput.trim());
      setUrlInput('');
      setShowUrlForm(false);
      setTimeout(load, 500);
    } catch (e: any) { alert(e.message); }
  };

  const addYoutube = async () => {
    if (!ytInput.trim()) return;
    try {
      await sourcesApi.addYoutube(id, ytInput.trim());
      setYtInput('');
      setShowYtForm(false);
      setTimeout(load, 500);
    } catch (e: any) { alert(e.message); }
  };

  const deleteSource = async (sourceId: number) => {
    if (!confirm('Delete this source?')) return;
    try {
      await sourcesApi.delete(sourceId);
      setSources((prev) => prev.filter((s: any) => s.id !== sourceId));
    } catch (e: any) { alert(e.message); }
  };

  if (loading) return (
    <DashboardLayout>
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full border-4 border-gray-200 border-t-purple-600 h-10 w-10" />
      </div>
    </DashboardLayout>
  );

  const completedCount = sources.filter((s: any) => s.status === 'completed').length;

  return (
    <DashboardLayout>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => router.push('/collections')} className="p-2 hover:bg-gray-100 rounded-xl"><ArrowLeft className="w-5 h-5 text-gray-500" /></button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{collection?.name}</h1>
          {collection?.description && <p className="text-sm text-gray-500 mt-0.5">{collection.description}</p>}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Sources', value: sources.length, color: 'bg-blue-50 text-blue-600' },
          { label: 'Processed', value: completedCount, color: 'bg-emerald-50 text-emerald-600' },
          { label: 'Questions', value: collection?.question_count || 0, color: 'bg-purple-50 text-purple-600' },
          { label: 'Generated', value: collection?.generated_count || 0, color: 'bg-amber-50 text-amber-600' },
        ].map((s) => (
          <div key={s.label} className={`${s.color} rounded-xl p-4 text-center`}>
            <div className="text-xl font-bold">{s.value}</div>
            <div className="text-xs font-medium mt-0.5 opacity-80">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Quick Links */}
      <div className="flex flex-wrap gap-2 mb-6">
        {[
          { href: `/chat?collection=${id}`, label: 'AI Chat', icon: '💬' },
          { href: `/study-generator?collection=${id}`, label: 'Generate Study Material', icon: '📚' },
          { href: `/duplicate-detector?collection=${id}`, label: 'Detect Duplicates', icon: '🔍' },
          { href: `/quiz?collection=${id}`, label: 'Take Quiz', icon: '📝' },
          { href: `/flashcards?collection=${id}`, label: 'Flashcards', icon: '🃏' },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="inline-flex items-center gap-1.5 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:border-purple-200 hover:bg-purple-50 transition-colors">
            <span>{l.icon}</span> {l.label}
          </Link>
        ))}
      </div>

      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-2xl p-8 text-center mb-6 transition-colors ${
          dragOver ? 'border-purple-400 bg-purple-50' : 'border-gray-200 bg-white hover:border-gray-300'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <Upload className={`w-10 h-10 mx-auto mb-3 ${dragOver ? 'text-purple-500' : 'text-gray-300'}`} />
        <p className="text-sm text-gray-600 mb-2">
          {uploading ? 'Uploading...' : 'Drag & drop files here, or click to browse'}
        </p>
        <p className="text-xs text-gray-400 mb-4">PDF, DOCX, PPTX, JPG, PNG (max 50MB each)</p>
        <div className="flex flex-wrap justify-center gap-2">
          <label className="cursor-pointer inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-medium hover:from-purple-700 hover:to-indigo-700">
            <Plus className="w-4 h-4" /> Upload Files
            <input type="file" multiple accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png" className="hidden" onChange={(e) => e.target.files && handleFiles(e.target.files)} />
          </label>
          <button onClick={() => setShowUrlForm(!showUrlForm)} className="inline-flex items-center gap-1.5 px-4 py-2 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">
            <Globe className="w-4 h-4" /> Add URL
          </button>
          <button onClick={() => setShowYtForm(!showYtForm)} className="inline-flex items-center gap-1.5 px-4 py-2 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50">
            <Youtube className="w-4 h-4" /> Add YouTube
          </button>
        </div>
      </div>

      {/* URL Input */}
      {showUrlForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4 flex gap-3">
          <input type="url" value={urlInput} onChange={(e) => setUrlInput(e.target.value)} placeholder="https://example.com/article"
            className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
          <button onClick={addUrl} className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium">Add</button>
        </div>
      )}
      {showYtForm && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 mb-4 flex gap-3">
          <input type="url" value={ytInput} onChange={(e) => setYtInput(e.target.value)} placeholder="https://youtube.com/watch?v=..."
            className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500" />
          <button onClick={addYoutube} className="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium">Add</button>
        </div>
      )}

      {/* Sources List */}
      <div className="bg-white rounded-2xl border border-gray-100">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Uploaded Sources ({sources.length})</h2>
        </div>
        {sources.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <p>No sources uploaded yet. Upload files above to get started.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {sources.map((s: any) => {
              const Icon = typeIcons[s.file_type] || FileText;
              const color = typeColors[s.file_type] || 'text-gray-500 bg-gray-50';
              return (
                <div key={s.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-gray-50/50">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{s.original_filename || s.url || 'Unknown'}</p>
                    <p className="text-xs text-gray-400">
                      {s.file_type.toUpperCase()}
                      {s.file_size && ` · ${(s.file_size / 1024 / 1024).toFixed(1)} MB`}
                      {s.page_count && ` · ${s.page_count} pages`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {s.status === 'completed' && <span className="flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full"><CheckCircle2 className="w-3 h-3" /> Ready</span>}
                    {s.status === 'processing' && <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full"><Loader2 className="w-3 h-3 animate-spin" /> Processing</span>}
                    {s.status === 'pending' && <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full"><Loader2 className="w-3 h-3" /> Pending</span>}
                    {s.status === 'failed' && (
                      <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2.5 py-1 rounded-full" title={s.error_message || ''}>
                        <XCircle className="w-3 h-3" /> Failed
                      </span>
                    )}
                    {s.status === 'failed' && (
                      <button onClick={() => sourcesApi.reprocess(s.id).then(() => setTimeout(load, 500))} className="p-1.5 hover:bg-gray-100 rounded-lg" title="Retry">
                        <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
                      </button>
                    )}
                    <button onClick={() => deleteSource(s.id)} className="p-1.5 hover:bg-red-50 rounded-lg">
                      <Trash2 className="w-3.5 h-3.5 text-gray-300 hover:text-red-500" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
