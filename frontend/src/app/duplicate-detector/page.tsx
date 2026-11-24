'use client';
import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, questionsApi, sourcesApi } from '@/lib/api';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';
import {
  GitCompareArrows,
  Upload,
  Download,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Layers,
  Copy,
  Sliders,
  Search,
  Trash2,
  X,
  Plus,
  FolderOpen,
  HelpCircle,
  FileCheck,
} from 'lucide-react';

interface StagedSource {
  id: number;
  filename: string;
  original_filename?: string;
  total_pages?: number;
  file_type?: string;
  status: string;
}

export default function DuplicateDetectorPage() {
  const searchParams = useSearchParams();
  const presetCol = searchParams.get('collection');

  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [browseColId, setBrowseColId] = useState<number>(0);

  // Staged sources for comparison - ALWAYS EMPTY BY DEFAULT
  const [stagedSources, setStagedSources] = useState<StagedSource[]>([]);
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(0.82);

  // UI Modes: 'upload' (direct drag-drop/file pick) or 'collection' (choose from existing)
  const [selectionMode, setSelectionMode] = useState<'upload' | 'collection'>('upload');
  const [browseSources, setBrowseSources] = useState<any[]>([]);
  const [loadingBrowseSources, setLoadingBrowseSources] = useState<boolean>(false);
  const [checkedSourceIds, setCheckedSourceIds] = useState<number[]>([]); // UNCHECKED BY DEFAULT

  // Drag and Drop state
  const [isDragging, setIsDragging] = useState(false);

  // Loading states
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [downloadingUniquePdf, setDownloadingUniquePdf] = useState(false);
  const [downloadingRepeatedPdf, setDownloadingRepeatedPdf] = useState(false);

  // Results & Display
  const [results, setResults] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'repeated' | 'unique'>('repeated');
  const [uniqueSearchQuery, setUniqueSearchQuery] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load collections on mount
  useEffect(() => {
    collectionsApi.list().then(async (cols: any[]) => {
      let list = cols;
      if (list.length === 0) {
        try {
          const defaultCol = await collectionsApi.create({
            name: 'Exam Papers & Past Questions',
            description: 'Collection for analyzing past exam papers and identifying duplicate questions',
          });
          list = [defaultCol];
        } catch (err) {
          console.error('Failed to create initial collection:', err);
        }
      }
      setCollections(list);
      if (presetCol) {
        const id = Number(presetCol);
        setSelectedCol(id);
        setBrowseColId(id);
      } else if (list.length > 0) {
        setSelectedCol(list[0].id);
        setBrowseColId(list[0].id);
      }
    }).catch((err) => {
      console.error('Failed to load collections:', err);
    });
  }, [presetCol]);

  // Load sources for "Browse Existing Collection" view
  useEffect(() => {
    if (!browseColId) {
      setBrowseSources([]);
      setCheckedSourceIds([]);
      return;
    }
    setLoadingBrowseSources(true);
    setCheckedSourceIds([]); // strictly unchecked by default
    sourcesApi.list(browseColId).then((items: any[]) => {
      setBrowseSources(items || []);
    }).catch((err) => {
      console.error('Failed to load sources for collection:', err);
      setBrowseSources([]);
    }).finally(() => {
      setLoadingBrowseSources(false);
    });
  }, [browseColId]);

  // Direct File Validation & Upload Handling
  const handleFiles = async (files: File[]) => {
    setErrorMsg(null);
    setSuccessMsg(null);

    if (!files || files.length === 0) return;

    // Validate files: PDF only, max 50MB, no duplicate filenames
    const validFiles: File[] = [];
    const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

    for (const file of files) {
      const isPdf = file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf';
      if (!isPdf) {
        setErrorMsg(`Only PDF files (.pdf) are supported. "${file.name}" was skipped.`);
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        setErrorMsg(`File "${file.name}" exceeds the maximum allowed size of 50MB.`);
        continue;
      }
      const isDuplicateName = stagedSources.some(
        (s) => (s.original_filename || s.filename).toLowerCase() === file.name.toLowerCase()
      );
      if (isDuplicateName) {
        setErrorMsg(`File "${file.name}" is already staged for comparison.`);
        continue;
      }
      validFiles.push(file);
    }

    if (validFiles.length === 0) return;

    // Ensure we have a valid collection to upload into
    let targetColId = selectedCol;
    if (!targetColId && collections.length > 0) {
      targetColId = collections[0].id;
      setSelectedCol(targetColId);
    }

    setUploadingFiles(true);
    try {
      const uploadResp: any = await sourcesApi.upload(targetColId, validFiles);
      const newSources = uploadResp.sources || [];
      const newSourceIds = newSources.map((s: any) => s.id);

      // Poll until newly uploaded files finish background processing (text/OCR)
      const deadline = Date.now() + 120000;
      let latestList: any[] = [];
      while (Date.now() < deadline) {
        latestList = await sourcesApi.list(targetColId);
        const processingNow = latestList.filter(
          (s: any) => newSourceIds.includes(s.id) && ['processing', 'pending'].includes(s.status)
        );
        if (processingNow.length === 0) break;
        await new Promise((r) => setTimeout(r, 1500));
      }

      // Add completed sources to staged list
      const newlyCompleted = latestList.filter((s: any) => newSourceIds.includes(s.id) && s.status === 'completed');
      if (newlyCompleted.length > 0) {
        setStagedSources((prev) => {
          const existingIds = new Set(prev.map((p) => p.id));
          const toAdd = newlyCompleted.filter((n: any) => !existingIds.has(n.id));
          return [...prev, ...toAdd];
        });
        setSuccessMsg(`Successfully uploaded and staged ${newlyCompleted.length} question paper(s).`);
      } else if (newSourceIds.length > 0) {
        setErrorMsg('Uploaded files are still processing. Please wait a moment and try again.');
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'File upload failed. Please try again.');
    } finally {
      setUploadingFiles(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  // Remove single staged source
  const handleRemoveStaged = (id: number) => {
    setStagedSources((prev) => prev.filter((s) => s.id !== id));
  };

  // Clear all staged sources
  const handleClearAllStaged = () => {
    setStagedSources([]);
    setResults(null);
  };

  // Checklist toggles for "Select from Existing Collection"
  const toggleBrowseCheck = (id: number) => {
    setCheckedSourceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAllBrowse = () => {
    const readyIds = browseSources.filter((s) => s.status === 'completed').map((s) => s.id);
    setCheckedSourceIds(readyIds);
  };

  const handleDeselectAllBrowse = () => {
    setCheckedSourceIds([]);
  };

  // Add checked collection items to Staged Sources
  const handleAddCheckedToStaged = () => {
    if (checkedSourceIds.length === 0) return;
    const selectedItems = browseSources.filter((s) => checkedSourceIds.includes(s.id));
    setStagedSources((prev) => {
      const existingIds = new Set(prev.map((p) => p.id));
      const toAdd = selectedItems.filter((item) => !existingIds.has(item.id));
      return [...prev, ...toAdd];
    });
    setCheckedSourceIds([]);
    setSuccessMsg(`Added ${selectedItems.length} question paper(s) to comparison list.`);
    setSelectionMode('upload'); // Return to main staging view
  };

  // Run Duplicate Detection
  const handleDetectDuplicates = async () => {
    if (stagedSources.length < 2) {
      setErrorMsg('Please stage at least 2 question papers to compare and detect duplicate questions.');
      return;
    }

    setAnalyzing(true);
    setErrorMsg(null);

    const sourceIds = stagedSources.map((s) => s.id);
    const targetColId = selectedCol || (collections.length > 0 ? collections[0].id : 1);

    try {
      const res = await questionsApi.detectDuplicates(targetColId, {
        source_ids: sourceIds,
        similarity_threshold: similarityThreshold,
        use_llm_verification: false,
      });
      setResults(res);
      if (res.repeated_question_groups_count > 0 || (res.repeated_question_groups && res.repeated_question_groups.length > 0)) {
        setActiveTab('repeated');
      } else {
        setActiveTab('unique');
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to detect duplicates. Please ensure the documents contain readable questions.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Download Unique Questions PDF (Report 1)
  const handleDownloadUniquePdf = async () => {
    if (stagedSources.length === 0) return;
    setDownloadingUniquePdf(true);
    const sourceIds = stagedSources.map((s) => s.id);
    const targetColId = selectedCol || (collections.length > 0 ? collections[0].id : 1);
    try {
      const blob = await questionsApi.exportUniqueQuestionsPdf(targetColId, {
        source_ids: sourceIds,
        similarity_threshold: similarityThreshold,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Source2Study_Unique_Questions_Report.pdf';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to generate Unique Questions PDF.');
    } finally {
      setDownloadingUniquePdf(false);
    }
  };

  // Download Repeated Questions PDF (Report 2)
  const handleDownloadRepeatedPdf = async () => {
    if (stagedSources.length === 0) return;
    setDownloadingRepeatedPdf(true);
    const sourceIds = stagedSources.map((s) => s.id);
    const targetColId = selectedCol || (collections.length > 0 ? collections[0].id : 1);
    try {
      const blob = await questionsApi.exportRepeatedQuestionsPdf(targetColId, {
        source_ids: sourceIds,
        similarity_threshold: similarityThreshold,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Source2Study_Repeated_Questions_Report.pdf';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to generate Repeated Questions PDF.');
    } finally {
      setDownloadingRepeatedPdf(false);
    }
  };

  // Extract result metrics safely
  const totalDocs = results?.total_documents ?? results?.total_sources ?? stagedSources.length;
  const totalPages = results?.total_pages_processed ?? results?.total_pages ?? 0;
  const totalQuestions = results?.total_questions ?? results?.total_questions_extracted ?? 0;
  const uniqueQuestionsCount = results?.unique_questions ?? results?.unique_questions_count ?? 0;
  const repeatedGroupsCount = results?.repeated_groups_count ?? results?.repeated_question_groups_count ?? 0;
  const totalDuplicates = results?.total_duplicate_occurrences ?? 0;
  const repeatedGroups = results?.repeated_question_groups ?? results?.duplicate_groups ?? [];
  const uniqueQuestionsList = results?.unique_questions_list ?? results?.unique_questions ?? [];

  const filteredUniqueQuestions = uniqueQuestionsList.filter((q: any) =>
    (q.question_text || '').toLowerCase().includes(uniqueSearchQuery.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto space-y-6 pb-16">
        {/* Page Header - Clean, professional, no internal labels */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <div className="w-9 h-9 bg-gradient-to-tr from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center text-white shadow-sm">
                <GitCompareArrows className="w-5 h-5" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900">Question Paper Duplicate Detector</h1>
            </div>
            <p className="text-sm text-gray-500">
              Upload multiple past-year question papers (PDF) to identify recurring exam questions, cross-match concepts, and download consolidated question banks.
            </p>
          </div>
        </div>

        {/* Alerts / Error Messages */}
        {errorMsg && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-700 text-sm">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold">Notice</p>
              <p className="text-xs text-red-600 mt-0.5">{errorMsg}</p>
            </div>
            <button onClick={() => setErrorMsg(null)} className="text-xs text-red-500 hover:text-red-700 underline font-medium">
              Dismiss
            </button>
          </div>
        )}

        {successMsg && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-3 text-emerald-800 text-sm">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-emerald-900">Success</p>
              <p className="text-xs text-emerald-700 mt-0.5">{successMsg}</p>
            </div>
            <button onClick={() => setSuccessMsg(null)} className="text-xs text-emerald-600 hover:text-emerald-800 underline font-medium">
              Dismiss
            </button>
          </div>
        )}

        {/* Document Selection Section */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          {/* Mode Switcher Tabs */}
          <div className="flex items-center border-b border-gray-100 bg-gray-50/50 px-6 pt-3 gap-3">
            <button
              onClick={() => setSelectionMode('upload')}
              className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
                selectionMode === 'upload'
                  ? 'border-purple-600 text-purple-700 font-bold'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              <Upload className="w-4 h-4" />
              <span>Direct PDF Upload</span>
            </button>

            <button
              onClick={() => setSelectionMode('collection')}
              className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all ${
                selectionMode === 'collection'
                  ? 'border-purple-600 text-purple-700 font-bold'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              <span>Select from Existing Collection</span>
            </button>
          </div>

          <div className="p-6">
            {/* Mode 1: Direct PDF Drag & Drop */}
            {selectionMode === 'upload' && (
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files) handleFiles(Array.from(e.target.files));
                  }}
                />

                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                    isDragging
                      ? 'border-purple-500 bg-purple-50/70 scale-[0.99]'
                      : 'border-gray-200 hover:border-purple-300 bg-gray-50/40 hover:bg-purple-50/20'
                  }`}
                >
                  <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-sm">
                    {uploadingFiles ? (
                      <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
                    ) : (
                      <Upload className="w-6 h-6" />
                    )}
                  </div>
                  <p className="text-sm font-bold text-gray-800 mb-1">
                    {uploadingFiles ? 'Uploading & Processing Question Papers...' : 'Drop Question Paper PDFs here, or click to browse'}
                  </p>
                  <p className="text-xs text-gray-500 max-w-md mx-auto">
                    Supported format: <span className="font-semibold text-gray-700">PDF (.pdf)</span> • Max file size: <span className="font-semibold text-gray-700">50MB</span>
                  </p>
                  <p className="text-[11px] text-gray-400 mt-1">
                    Upload multiple exam papers (e.g. GATE 2021, GATE 2022, GATE 2023) to discover duplicate and repeated questions.
                  </p>
                </div>
              </div>
            )}

            {/* Mode 2: Select from Existing Collection */}
            {selectionMode === 'collection' && (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Choose Collection:</span>
                    <select
                      value={browseColId}
                      onChange={(e) => setBrowseColId(Number(e.target.value))}
                      className="px-3 py-1.5 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500 cursor-pointer"
                    >
                      {collections.map((c: any) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-3 text-xs">
                    <button
                      onClick={handleSelectAllBrowse}
                      className="text-purple-600 hover:text-purple-800 font-semibold"
                    >
                      Select All Ready
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={handleDeselectAllBrowse}
                      className="text-gray-500 hover:text-gray-700 font-medium"
                    >
                      Deselect All
                    </button>
                  </div>
                </div>

                {loadingBrowseSources ? (
                  <div className="py-10 text-center">
                    <Loader2 className="w-6 h-6 animate-spin text-purple-600 mx-auto mb-2" />
                    <p className="text-xs text-gray-500">Loading collection documents...</p>
                  </div>
                ) : browseSources.length === 0 ? (
                  <div className="py-8 text-center bg-gray-50/50 rounded-xl border border-gray-100">
                    <p className="text-xs font-medium text-gray-500">No documents found in this collection.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-60 overflow-y-auto p-1">
                    {browseSources.map((source: any) => {
                      const isStaged = stagedSources.some((s) => s.id === source.id);
                      const isChecked = checkedSourceIds.includes(source.id);
                      const isReady = source.status === 'completed';

                      return (
                        <label
                          key={source.id}
                          className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                            isStaged
                              ? 'bg-purple-50/40 border-purple-200 opacity-80 cursor-default'
                              : isChecked
                              ? 'bg-purple-50 border-purple-300 shadow-sm cursor-pointer'
                              : 'bg-white border-gray-100 hover:border-gray-200 cursor-pointer'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isStaged || isChecked}
                            disabled={isStaged || !isReady}
                            onChange={() => toggleBrowseCheck(source.id)}
                            className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500"
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-gray-800 truncate">
                              {source.original_filename || source.filename}
                            </p>
                            <p className="text-[10px] text-gray-400">
                              {source.file_type?.toUpperCase()} • {source.total_pages || 1} page(s)
                            </p>
                          </div>
                          {isStaged ? (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                              Staged
                            </span>
                          ) : (
                            <span
                              className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                                isReady
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : 'bg-amber-50 text-amber-700'
                              }`}
                            >
                              {isReady ? 'Ready' : source.status}
                            </span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                )}

                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleAddCheckedToStaged}
                    disabled={checkedSourceIds.length === 0}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add to Comparison ({checkedSourceIds.length})</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Staged Question Papers Card */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-4">
            <div>
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-purple-600" />
                Staged Question Papers ({stagedSources.length})
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                These documents will be cross-analyzed to detect duplicate questions.
              </p>
            </div>

            {stagedSources.length > 0 && (
              <button
                onClick={handleClearAllStaged}
                className="text-xs font-medium text-red-600 hover:text-red-700 flex items-center gap-1 hover:underline"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear All Staged</span>
              </button>
            )}
          </div>

          {/* Staged List or Empty State */}
          {stagedSources.length === 0 ? (
            <div className="border border-dashed border-gray-200 rounded-xl p-8 text-center bg-gray-50/30">
              <GitCompareArrows className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-xs font-semibold text-gray-600">No question papers staged yet</p>
              <p className="text-[11px] text-gray-400 max-w-sm mx-auto mt-1">
                Upload at least 2 PDF question papers above or choose from your collections to begin duplicate detection.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {stagedSources.map((source, index) => (
                  <div
                    key={source.id}
                    className="p-3.5 rounded-xl border border-gray-200/80 bg-gray-50/60 flex items-center justify-between gap-2 shadow-xs hover:border-purple-200 transition-all"
                  >
                    <div className="w-8 h-8 rounded-lg bg-red-100 text-red-600 flex items-center justify-center flex-shrink-0 text-xs font-bold">
                      PDF
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-800 truncate" title={source.original_filename || source.filename}>
                        {source.original_filename || source.filename}
                      </p>
                      <p className="text-[10px] text-gray-500">
                        Paper #{index + 1} {source.total_pages ? `• ${source.total_pages} page(s)` : ''}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRemoveStaged(source.id)}
                      className="w-7 h-7 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 flex items-center justify-center transition-colors"
                      title="Remove from comparison"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>

              {stagedSources.length === 1 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-center gap-2.5 text-xs text-amber-800">
                  <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                  <span>
                    Add at least 1 more paper. Duplicate detection requires 2 or more question papers to compare and find repeated questions.
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Analysis Settings & Action Trigger */}
          <div className="mt-6 pt-5 border-t border-gray-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3 max-w-sm">
              <Sliders className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <div className="flex-1">
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-semibold text-gray-700">Similarity Sensitivity</span>
                  <span className="text-purple-600 font-bold">{Math.round(similarityThreshold * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.70"
                  max="0.95"
                  step="0.01"
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                  className="w-full accent-purple-600 cursor-pointer h-1.5 bg-gray-200 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                  <span>Broader (70%)</span>
                  <span>Balanced (82%)</span>
                  <span>Exact / Near (95%)</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleDetectDuplicates}
              disabled={stagedSources.length < 2 || analyzing || uploadingFiles}
              className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-sm font-semibold shadow-md shadow-purple-100 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Extracting Questions & Matching...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>
                    {stagedSources.length < 2
                      ? 'Add at Least 2 Papers to Analyze'
                      : `Analyze & Detect Duplicates (${stagedSources.length} Papers)`}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {results && (
          <div className="space-y-6">
            {/* 6 Metrics Summary Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Papers Processed</p>
                <p className="text-2xl font-extrabold text-gray-900">{totalDocs}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">{totalPages} total page(s)</p>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Questions Found</p>
                <p className="text-2xl font-extrabold text-indigo-600">{totalQuestions}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">Total across papers</p>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Unique Questions</p>
                <p className="text-2xl font-extrabold text-emerald-600">{uniqueQuestionsCount}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">Appeared only once</p>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Repeated Groups</p>
                <p className="text-2xl font-extrabold text-purple-600">{repeatedGroupsCount}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">Repeated across papers</p>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Duplicate Repetitions</p>
                <p className="text-2xl font-extrabold text-amber-600">{totalDuplicates}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">Extra question instances</p>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Repetition Rate</p>
                <p className="text-2xl font-extrabold text-teal-600">
                  {totalQuestions > 0
                    ? `${Math.round((totalDuplicates / totalQuestions) * 100)}%`
                    : '0%'}
                </p>
                <p className="text-[10px] text-gray-400 mt-0.5">Overlap percentage</p>
              </div>
            </div>

            {/* Download Reports Banner */}
            <div className="bg-gradient-to-r from-purple-50 via-indigo-50 to-purple-50 border border-purple-100 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                  <Download className="w-4 h-4 text-purple-600" />
                  Download Consolidated PDF Reports
                </h3>
                <p className="text-xs text-gray-600 mt-0.5">
                  Export professional, print-ready reports with source citations, page numbers, and occurrence breakdowns.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                {/* PDF 1: Unique Questions PDF */}
                <button
                  onClick={handleDownloadUniquePdf}
                  disabled={downloadingUniquePdf}
                  className="flex-1 md:flex-initial px-4 py-2.5 bg-white hover:bg-gray-50 text-gray-800 border border-gray-200 rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {downloadingUniquePdf ? (
                    <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
                  ) : (
                    <Download className="w-4 h-4 text-emerald-600" />
                  )}
                  <span>Download Unique Questions PDF</span>
                </button>

                {/* PDF 2: Repeated Questions PDF */}
                <button
                  onClick={handleDownloadRepeatedPdf}
                  disabled={downloadingRepeatedPdf}
                  className="flex-1 md:flex-initial px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {downloadingRepeatedPdf ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 text-white" />
                  )}
                  <span>Download Repeated Questions PDF</span>
                </button>
              </div>
            </div>

            {/* Results Tabs & Explorer */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              {/* Tab Navigation */}
              <div className="flex items-center border-b border-gray-100 px-6 pt-4 gap-6">
                <button
                  onClick={() => setActiveTab('repeated')}
                  className={`pb-3.5 text-sm font-semibold transition-all flex items-center gap-2 border-b-2 ${
                    activeTab === 'repeated'
                      ? 'border-purple-600 text-purple-700'
                      : 'border-transparent text-gray-500 hover:text-gray-800'
                  }`}
                >
                  <Copy className="w-4 h-4" />
                  <span>Repeated Questions ({repeatedGroupsCount})</span>
                </button>

                <button
                  onClick={() => setActiveTab('unique')}
                  className={`pb-3.5 text-sm font-semibold transition-all flex items-center gap-2 border-b-2 ${
                    activeTab === 'unique'
                      ? 'border-purple-600 text-purple-700'
                      : 'border-transparent text-gray-500 hover:text-gray-800'
                  }`}
                >
                  <Layers className="w-4 h-4" />
                  <span>Unique Questions ({uniqueQuestionsCount})</span>
                </button>
              </div>

              {/* Tab 1 Content: Repeated Questions */}
              {activeTab === 'repeated' && (
                <div className="p-6 space-y-4">
                  {repeatedGroups.length === 0 ? (
                    <div className="text-center py-12">
                      <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
                      <p className="text-base font-bold text-gray-800">No Repeated Questions Found</p>
                      <p className="text-xs text-gray-500 max-w-md mx-auto mt-1">
                        All extracted questions across your staged papers are distinct at the {Math.round(similarityThreshold * 100)}% threshold.
                      </p>
                    </div>
                  ) : (
                    repeatedGroups.map((group: any, idx: number) => {
                      const occurrences = group.frequency ?? group.occurrences_count ?? (group.members?.length || 0);
                      const membersList = group.members || group.sources || [];
                      return (
                        <div
                          key={idx}
                          className="p-5 rounded-2xl border border-gray-100 bg-gray-50/50 hover:bg-gray-50 transition-all space-y-3"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <span className="text-xs font-bold text-purple-700 bg-purple-100 px-2.5 py-1 rounded-lg">
                              Repeated Question #{idx + 1}
                            </span>
                            <span className="text-xs font-bold bg-amber-100 text-amber-800 px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                              <Copy className="w-3 h-3" />
                              Appeared in {occurrences} question papers
                            </span>
                          </div>

                          {/* Canonical Question with Markdown Rendering */}
                          <div className="bg-white p-4 rounded-xl border border-gray-100">
                            <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
                              Standard Question Text:
                            </p>
                            <MarkdownRenderer content={group.canonical_question || ''} />
                          </div>

                          {/* Recurrence Sources */}
                          <div>
                            <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-2">
                              Occurrences Across Exam Papers:
                            </p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                              {membersList.map((occ: any, occIdx: number) => (
                                <div
                                  key={occIdx}
                                  className="bg-white p-3 rounded-xl border border-gray-100 flex items-center justify-between text-xs"
                                >
                                  <div className="truncate mr-2">
                                    <p className="font-semibold text-gray-800 truncate">
                                      {occ.source_filename || occ.filename || 'Exam Paper'}
                                      {occ.question_number && occ.question_number !== 'Q' ? ` (${occ.question_number})` : ''}
                                    </p>
                                    <p className="text-[11px] text-gray-400">
                                      {occ.year ? `${occ.year} • ` : ''}{occ.page_number ? `Page ${occ.page_number}` : 'Document body'}
                                    </p>
                                  </div>
                                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border flex-shrink-0 ${
                                    occ.match_type === 'Exact Duplicate' || occ.match_type === 'Exact Match'
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-100'
                                      : occ.match_type === 'Near Duplicate' || occ.match_type === 'High Similarity'
                                      ? 'bg-amber-50 text-amber-700 border-amber-100'
                                      : 'bg-purple-50 text-purple-700 border-purple-100'
                                  }`}>
                                    {occ.match_type || 'Match'}{occ.similarity_score ? ` (${Math.round(occ.similarity_score * 100)}%)` : ''}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}

              {/* Tab 2 Content: Unique Questions */}
              {activeTab === 'unique' && (
                <div className="p-6 space-y-4">
                  {/* Search Bar */}
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Search within unique questions..."
                        value={uniqueSearchQuery}
                        onChange={(e) => setUniqueSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-purple-500 focus:bg-white transition-all"
                      />
                    </div>
                  </div>

                  {filteredUniqueQuestions.length === 0 ? (
                    <div className="text-center py-10">
                      <p className="text-sm text-gray-500">No questions match your search.</p>
                    </div>
                  ) : (
                    <div className="divide-y divide-gray-100">
                      {filteredUniqueQuestions.map((q: any, idx: number) => {
                        const sourcesList = q.all_sources && q.all_sources.length > 0
                          ? q.all_sources.map((s: any) => `${s.source_filename || 'Exam Paper'}${s.year ? ` (${s.year})` : ''}${s.question_number ? ` ${s.question_number}` : ''}${s.page_number ? ` [p. ${s.page_number}]` : ''}`)
                          : (q.appears_in_sources || [q.source_filename || q.filename || 'Exam Paper']);

                        return (
                          <div key={idx} className="py-4 first:pt-0 last:pb-0 space-y-2">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md">
                                  #{idx + 1}
                                </span>
                                {q.topic && (
                                  <span className="text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-100">
                                    {q.topic}
                                  </span>
                                )}
                                {q.question_type && (
                                  <span className="text-[10px] font-bold uppercase text-gray-500 bg-gray-50 px-1.5 py-0.5 rounded border border-gray-200">
                                    {q.question_type}
                                  </span>
                                )}
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {sourcesList.map((src: string, srcIdx: number) => (
                                  <span
                                    key={srcIdx}
                                    className="text-[11px] font-medium bg-gray-100 text-gray-700 px-2 py-0.5 rounded-md"
                                  >
                                    Found in: {src}
                                  </span>
                                ))}
                              </div>
                            </div>

                            {/* Question statement with Markdown Rendering */}
                            <div className="text-sm text-gray-800 leading-relaxed bg-white p-3 rounded-xl border border-gray-50">
                              <MarkdownRenderer content={q.question_text || ''} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
