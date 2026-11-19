'use client';
import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, questionsApi, sourcesApi } from '@/lib/api';
import { Loader2, Sparkles, Upload, GitCompareArrows } from 'lucide-react';

export default function DuplicateDetectorPage() {
  const searchParams = useSearchParams();
  const presetCol = searchParams.get('collection');
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const [deduplicating, setDeduplicating] = useState(false);
  const [deduplicatedDocument, setDeduplicatedDocument] = useState<any>(null);
  const [documentFormat, setDocumentFormat] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    collectionsApi.list().then((items: any[]) => {
      setCollections(items);
      if (presetCol) setSelectedCol(Number(presetCol));
      else if (items.length) setSelectedCol(items[0].id);
    });
  }, [presetCol]);

  useEffect(() => {
    if (!selectedCol) {
      setSources([]);
      setSelectedSourceIds([]);
      return;
    }
    setSources([]);
    setSelectedSourceIds([]);
    setDeduplicatedDocument(null);
    const storageKey = `studymind:duplicate-detector:sources:${selectedCol}`;
    let savedIds: number[] = [];
    try { savedIds = JSON.parse(localStorage.getItem(storageKey) || '[]').map(Number); } catch { /* Ignore invalid local upload history. */ }
    if (!savedIds.length) return;
    sourcesApi.list(selectedCol).then((items: any[]) => {
      const uploadedHere = items.filter((item) => savedIds.includes(item.id));
      setSources(uploadedHere);
      setSelectedSourceIds(uploadedHere.filter((item) => item.status === 'completed').map((item) => item.id));
    }).catch(() => setSources([]));
  }, [selectedCol]);

  const selectFiles = async (fileList: FileList | null) => {
    if (!selectedCol || !fileList?.length) return;
    const files = Array.from(fileList);
    setUploadingFiles(true);
    setDeduplicatedDocument(null);
    try {
      const uploadResult: any = await sourcesApi.upload(selectedCol, files);
      const ids = (uploadResult.sources || []).map((source: any) => source.id);
      if (!ids.length) throw new Error(uploadResult.message || 'No files were accepted');

      const storageKey = `studymind:duplicate-detector:sources:${selectedCol}`;
      let previousIds: number[] = [];
      try { previousIds = JSON.parse(localStorage.getItem(storageKey) || '[]').map(Number); } catch { /* Start a clean list. */ }
      const pageUploadIds = Array.from(new Set([...previousIds, ...ids]));
      localStorage.setItem(storageKey, JSON.stringify(pageUploadIds));

      const deadline = Date.now() + 120000;
      let latest: any[] = [];
      while (Date.now() < deadline) {
        latest = await sourcesApi.list(selectedCol);
        const justUploaded = latest.filter((source: any) => ids.includes(source.id));
        if (justUploaded.length === ids.length && justUploaded.every((source: any) => ['completed', 'failed'].includes(source.status))) break;
        await new Promise((resolve) => setTimeout(resolve, 1200));
      }
      setSources(latest.filter((source: any) => pageUploadIds.includes(source.id)));
      const ready = latest.filter((source: any) => ids.includes(source.id) && source.status === 'completed');
      setSelectedSourceIds(ready.map((source: any) => source.id));
      const failed = latest.filter((source: any) => ids.includes(source.id) && source.status === 'failed');
      if (failed.length) alert(failed.map((source: any) => `${source.original_filename}: ${source.error_message || 'processing failed'}`).join('\n'));
    } catch (e: any) {
      alert(e.message || 'File upload failed');
    } finally {
      setUploadingFiles(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  };

  const runDeduplication = async () => {
    if (!selectedCol || !selectedSourceIds.length) return;
    setDeduplicating(true);
    setDeduplicatedDocument(null);
    try {
      setDeduplicatedDocument(await questionsApi.deduplicateDocuments(selectedCol, selectedSourceIds));
    } catch (e: any) {
      alert(e.message || 'Could not remove duplicate content');
    } finally {
      setDeduplicating(false);
    }
  };

  const downloadDeduplicated = async (format: 'pdf' | 'docx') => {
    if (!selectedCol || !selectedSourceIds.length) return;
    setDocumentFormat(format);
    try {
      const blob = await questionsApi.exportDeduplicatedDocuments(selectedCol, selectedSourceIds, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `duplicate_free_study_material.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(e.message || 'Document download failed');
    } finally {
      setDocumentFormat(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-lg flex items-center justify-center">
            <GitCompareArrows className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Smart Duplicate Detector</h1>
          <span className="text-xs font-bold bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-2 py-0.5 rounded-full ml-1">SIGNATURE</span>
        </div>
        <p className="text-gray-500 text-sm mt-1">Upload study files, remove repeated passages, and download one clean document</p>
      </div>

      <section className="bg-white rounded-2xl border border-gray-100 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="font-semibold text-gray-900">Create a duplicate-free document</h2>
            <p className="text-sm text-gray-500 mt-1">Choose files from your PC. Repeated lines and passages are removed locally.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select value={selectedCol} onChange={(e) => setSelectedCol(Number(e.target.value))}
              className="px-3 py-2.5 bg-white border border-gray-200 rounded-xl text-sm min-w-[170px]">
              <option value={0}>Select Collection</option>
              {collections.map((collection: any) => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
            </select>
            <input ref={fileInput} type="file" multiple accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png" className="hidden"
              onChange={(event) => selectFiles(event.target.files)} />
            <button onClick={() => fileInput.current?.click()} disabled={!selectedCol || uploadingFiles}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-purple-200 text-purple-700 hover:bg-purple-50 disabled:opacity-50 text-sm font-medium">
              <Upload className="w-4 h-4" /> {uploadingFiles ? 'Uploading and reading files…' : 'Upload files'}
            </button>
          </div>
        </div>

        <div className="max-h-52 overflow-y-auto divide-y divide-gray-100 border border-gray-100 rounded-xl">
          {sources.length ? sources.map((source: any) => (
            <label key={source.id} className="flex items-center gap-3 px-3 py-2.5 text-sm">
              <input type="checkbox" checked={selectedSourceIds.includes(source.id)} disabled={source.status !== 'completed'}
                onChange={() => setSelectedSourceIds((ids) => ids.includes(source.id) ? ids.filter((id) => id !== source.id) : [...ids, source.id])}
                className="w-4 h-4 rounded text-purple-600" />
              <span className="flex-1 truncate text-gray-700">{source.original_filename || source.filename}</span>
              <span className={`text-xs ${source.status === 'completed' ? 'text-emerald-600' : source.status === 'failed' ? 'text-red-600' : 'text-amber-600'}`}>
                {source.status === 'completed' ? 'Ready' : source.status === 'failed' ? `Failed: ${source.error_message || ''}` : source.status}
              </span>
            </label>
          )) : <p className="px-3 py-5 text-sm text-gray-400">No files uploaded from this page yet. Upload PDF, DOCX, PPTX, JPG, or PNG files.</p>}
        </div>

        <div className="flex flex-wrap items-center gap-3 mt-4">
          <button onClick={runDeduplication} disabled={!selectedSourceIds.length || uploadingFiles || deduplicating}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-medium disabled:opacity-50">
            {deduplicating ? <><Loader2 className="w-4 h-4 animate-spin" /> Removing duplicates…</> : <><Sparkles className="w-4 h-4" /> Remove duplicates</>}
          </button>
          {deduplicatedDocument && <span className="text-sm text-emerald-700">Removed {deduplicatedDocument.duplicates_removed} repeated passages; {deduplicatedDocument.unique_passage_count} unique passages remain.</span>}
        </div>

        {deduplicatedDocument && (
          <div className="mt-4 border border-gray-100 rounded-xl overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-gray-50 border-b border-gray-100">
              <span className="text-sm font-medium text-gray-800">Preview — {deduplicatedDocument.source_count} file(s)</span>
              <div className="flex gap-2">
                {(['pdf', 'docx'] as const).map((format) => <button key={format} onClick={() => downloadDeduplicated(format)} disabled={!!documentFormat}
                  className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-700 disabled:opacity-50">
                  {documentFormat === format ? 'Preparing…' : `Download ${format.toUpperCase()}`}
                </button>)}
              </div>
            </div>
            <pre className="p-4 max-h-80 overflow-auto whitespace-pre-wrap text-sm text-gray-700 font-sans">{deduplicatedDocument.content}{deduplicatedDocument.preview_truncated ? '\n\n…Preview shortened. Download the full document above.' : ''}</pre>
          </div>
        )}
      </section>
    </DashboardLayout>
  );
}
