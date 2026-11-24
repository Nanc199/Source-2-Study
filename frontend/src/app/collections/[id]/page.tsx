'use client';
import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, sourcesApi } from '@/lib/api';
import {
  ArrowLeft, Upload, FileText, Globe, Youtube, Image, Trash2,
  CheckCircle2, XCircle, Loader2, RefreshCw, Plus, AlertCircle
} from 'lucide-react';

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
  const [addingUrl, setAddingUrl] = useState(false);
  const [addingYt, setAddingYt] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [ytInput, setYtInput] = useState('');
  const [showUrlForm, setShowUrlForm] = useState(false);
  const [showYtForm, setShowYtForm] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

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
    }, 2500);
    return () => clearInterval(interval);
  }, [sources, id]);

  const handleFiles = async (files: FileList | File[]) => {
    if (!files.length) return;
    setUploading(true);
    setActionError(null);
    try {
      await sourcesApi.upload(id, Array.from(files));
      setTimeout(load, 500);
    } catch (e: any) {
      setActionError(e?.message || 'File upload failed');
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
    let cleanUrl = urlInput.trim();
    if (!cleanUrl) return;
    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      cleanUrl = `https://${cleanUrl}`;
    }

    setAddingUrl(true);
    setActionError(null);
    try {
      await sourcesApi.addUrl(id, cleanUrl);
      setUrlInput('');
      setShowUrlForm(false);
      setTimeout(load, 500);
    } catch (e: any) {
      setActionError(e?.message || 'Failed to add URL resource. Please ensure the link is public and accessible.');
    } finally {
      setAddingUrl(false);
    }
  };

  const addYoutube = async () => {
    let cleanUrl = ytInput.trim();
    if (!cleanUrl) return;
    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      cleanUrl = `https://${cleanUrl}`;
    }

    setAddingYt(true);
    setActionError(null);
    try {
      await sourcesApi.addYoutube(id, cleanUrl);
      setYtInput('');
      setShowYtForm(false);
      setTimeout(load, 500);
    } catch (e: any) {
      setActionError(e?.message || 'Failed to add YouTube video. Please check the URL.');
    } finally {
      setAddingYt(false);
    }
  };

  const deleteSource = async (sourceId: number) => {
    if (!confirm('Are you sure you want to delete this study resource?')) return;
    try {
      await sourcesApi.delete(sourceId);
      setSources((prev) => prev.filter((s: any) => s.id !== sourceId));
    } catch (e: any) {
      setActionError(e?.message || 'Failed to delete resource');
    }
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
        <button onClick={() => router.push('/collections')} className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{collection?.name}</h1>
          {collection?.description && <p className="text-sm text-gray-500 mt-0.5">{collection.description}</p>}
        </div>
      </div>

      {actionError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 text-sm">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Resource Ingestion Notice</p>
            <p className="text-xs text-red-600 mt-0.5">{actionError}</p>
          </div>
          <button onClick={() => setActionError(null)} className="text-xs text-red-500 hover:text-red-700 underline">
            Dismiss
          </button>
        </div>
      )}

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
          {uploading ? 'Uploading and processing files...' : 'Drag & drop files here, or click to browse'}
        </p>
        <p className="text-xs text-gray-400 mb-4">PDF, Scanned PDFs, DOCX, PPTX, JPG, PNG (max 50MB each)</p>
        <div className="flex flex-wrap justify-center gap-2">
          <label className="cursor-pointer inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-medium hover:from-purple-700 hover:to-indigo-700 shadow-sm">
            <Plus className="w-4 h-4" /> Upload Files
            <input type="file" multiple accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png" className="hidden" onChange={(e) => e.target.files && handleFiles(e.target.files)} />
          </label>
          <button
            onClick={() => { setShowUrlForm(!showUrlForm); setShowYtForm(false); }}
            className={`inline-flex items-center gap-1.5 px-4 py-2 border rounded-xl text-sm font-medium transition-all ${
              showUrlForm ? 'bg-purple-50 border-purple-300 text-purple-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Globe className="w-4 h-4" /> Add Webpage URL
          </button>
          <button
            onClick={() => { setShowYtForm(!showYtForm); setShowUrlForm(false); }}
            className={`inline-flex items-center gap-1.5 px-4 py-2 border rounded-xl text-sm font-medium transition-all ${
              showYtForm ? 'bg-rose-50 border-rose-300 text-rose-700' : 'border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Youtube className="w-4 h-4" /> Add YouTube
          </button>
        </div>
      </div>

      {/* URL Input Form */}
      {showUrlForm && (
        <div className="bg-white border border-purple-200 rounded-xl p-4 mb-4 shadow-sm">
          <p className="text-xs font-semibold text-gray-700 mb-2">Fetch & Ingest Web Article or Online Notes:</p>
          <div className="flex gap-2">
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addUrl()}
              disabled={addingUrl}
              placeholder="https://en.wikipedia.org/wiki/Computer_science or example.com/article"
              className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
            />
            <button
              onClick={addUrl}
              disabled={!urlInput.trim() || addingUrl}
              className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-sm font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {addingUrl ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
              <span>{addingUrl ? 'Extracting...' : 'Add URL'}</span>
            </button>
          </div>
          <p className="text-[11px] text-gray-400 mt-2">
            Source2Study extracts readable text and article bodies safely. SSRF protected.
          </p>
        </div>
      )}

      {/* YouTube Input Form */}
      {showYtForm && (
        <div className="bg-white border border-rose-200 rounded-xl p-4 mb-4 shadow-sm">
          <p className="text-xs font-semibold text-gray-700 mb-2">Ingest YouTube Video Lecture / Transcript:</p>
          <div className="flex gap-2">
            <input
              type="url"
              value={ytInput}
              onChange={(e) => setYtInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addYoutube()}
              disabled={addingYt}
              placeholder="https://www.youtube.com/watch?v=..."
              className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 disabled:opacity-50"
            />
            <button
              onClick={addYoutube}
              disabled={!ytInput.trim() || addingYt}
              className="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-sm font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {addingYt ? <Loader2 className="w-4 h-4 animate-spin" /> : <Youtube className="w-4 h-4" />}
              <span>{addingYt ? 'Fetching...' : 'Add Video'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Sources List */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Uploaded Study Resources ({sources.length})</h2>
          {completedCount > 0 && (
            <span className="text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full font-medium">
              {completedCount} ready for study & analysis
            </span>
          )}
        </div>
        {sources.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="font-medium text-gray-600">No resources in this collection yet.</p>
            <p className="text-xs text-gray-400 mt-1">Upload PDF question papers, documents, or add web URLs above.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {sources.map((s: any) => {
              const Icon = typeIcons[s.file_type] || FileText;
              const color = typeColors[s.file_type] || 'text-gray-500 bg-gray-50';
              return (
                <div key={s.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-gray-50/50 transition-colors">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color} flex-shrink-0`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {s.original_filename || s.url || 'Untitled Resource'}
                    </p>
                    <p className="text-xs text-gray-400 flex items-center gap-2 mt-0.5">
                      <span className="font-semibold uppercase">{s.file_type}</span>
                      {s.file_size ? <span>· {(s.file_size / 1024 / 1024).toFixed(2)} MB</span> : null}
                      {s.total_pages ? <span>· {s.total_pages} page(s)</span> : null}
                    </p>
                    {s.status === 'failed' && s.error_message && (
                      <p className="text-xs text-red-600 mt-1 font-medium">
                        Reason: {s.error_message}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {s.status === 'completed' && (
                      <span className="flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Ready
                      </span>
                    )}
                    {s.status === 'processing' && (
                      <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full font-medium">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing
                      </span>
                    )}
                    {s.status === 'pending' && (
                      <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full font-medium">
                        <Loader2 className="w-3.5 h-3.5" /> Queued
                      </span>
                    )}
                    {s.status === 'failed' && (
                      <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2.5 py-1 rounded-full font-medium">
                        <XCircle className="w-3.5 h-3.5" /> Failed
                      </span>
                    )}
                    {s.status === 'failed' && (
                      <button
                        onClick={() => sourcesApi.reprocess(s.id).then(() => setTimeout(load, 500))}
                        className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-purple-600"
                        title="Retry Processing"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={() => deleteSource(s.id)}
                      className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
                      title="Delete Source"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
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
