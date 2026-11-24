'use client';
import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';
import { collectionsApi, chatApi } from '@/lib/api';
import { Send, Plus, MessageSquare, Trash2, Sparkles, Copy, Check, BookOpen } from 'lucide-react';

export default function ChatPage() {
  const searchParams = useSearchParams();
  const presetCol = searchParams.get('collection');

  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<number | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load collections or auto-create default if empty
  useEffect(() => {
    collectionsApi.list().then(async (cols: any[]) => {
      let list = cols;
      if (list.length === 0) {
        try {
          const defaultCol = await collectionsApi.create({
            name: 'General Study',
            description: 'Default collection for Source2Study learning materials',
          });
          list = [defaultCol];
        } catch (err) {
          console.error('Failed to auto-create default collection:', err);
        }
      }
      setCollections(list);
      if (presetCol) {
        setSelectedCol(Number(presetCol));
      } else if (list.length > 0) {
        setSelectedCol(list[0].id);
      }
    }).catch((err) => {
      console.error('Error loading collections:', err);
    });
  }, [presetCol]);

  // Load chat sessions when collection changes
  useEffect(() => {
    if (!selectedCol) return;
    chatApi.listSessions(selectedCol)
      .then((sess: any[]) => {
        setSessions(sess);
        // Reset to a clean, active new chat view ready for typing
        setActiveSession(null);
        setMessages([]);
      })
      .catch(() => {
        setSessions([]);
        setActiveSession(null);
        setMessages([]);
      });
  }, [selectedCol]);

  // Load messages when an existing session is selected
  useEffect(() => {
    if (!activeSession) return;
    chatApi.getMessages(activeSession)
      .then((msgs: any[]) => setMessages(msgs))
      .catch(() => setMessages([]));
  }, [activeSession]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, [activeSession]);

  const handleStartNewChat = () => {
    setActiveSession(null);
    setMessages([]);
    setInput('');
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: number) => {
    e.stopPropagation();
    try {
      await chatApi.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSession === sessionId) {
        setActiveSession(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const sendMessage = async (textToSend?: string) => {
    const content = (textToSend || input).trim();
    if (!content || sending) return;

    let targetColId = selectedCol;
    if (!targetColId && collections.length > 0) {
      targetColId = collections[0].id;
      setSelectedCol(targetColId);
    }

    if (!targetColId) {
      try {
        const newCol = await collectionsApi.create({
          name: 'General Study',
          description: 'Default collection for Source2Study learning materials',
        });
        setCollections([newCol]);
        targetColId = newCol.id;
        setSelectedCol(targetColId);
      } catch (err) {
        console.error('Failed to create collection:', err);
        return;
      }
    }

    setInput('');
    const tempUserMsgId = Date.now();
    setMessages((prev) => [
      ...prev,
      { id: tempUserMsgId, role: 'user', content, created_at: new Date().toISOString() },
    ]);
    setSending(true);

    try {
      let currentSessionId: number;
      if (activeSession) {
        currentSessionId = activeSession;
      } else {
        // Automatically create a new conversation session
        const sessionTitle = content.length > 45 ? `${content.slice(0, 45)}...` : content;
        const newSession = await chatApi.createSession(targetColId, sessionTitle);
        currentSessionId = newSession.id;
        setActiveSession(currentSessionId);
        setSessions((prev) => [newSession, ...prev]);
      }

      const response = await chatApi.sendMessage(currentSessionId, content);

      // Update session title if default
      setSessions((prev) =>
        prev.map((s) =>
          s.id === currentSessionId
            ? {
                ...s,
                title: s.title === 'New Chat' ? (content.length > 45 ? `${content.slice(0, 45)}...` : content) : s.title,
                message_count: (s.message_count || 0) + 2,
              }
            : s
        )
      );

      setMessages((prev) => [...prev, response]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: `Error: ${err?.message || 'Could not retrieve AI response. Please ensure your collection has sources uploaded or try again.'}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const copyText = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const suggestedPrompts = [
    'Summarize all uploaded study materials',
    'Explain the core topics and definitions simply',
    'Generate 5 important practice questions with solutions',
    'Compare the main formulas and key distinctions',
  ];

  const activeSessionTitle = sessions.find((s) => s.id === activeSession)?.title;

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-7rem)] gap-4">
        {/* Left Sidebar: Collection Selector, Single New Chat Button & Chat History */}
        <div className="w-72 bg-white rounded-2xl border border-gray-100 flex flex-col flex-shrink-0 shadow-sm">
          {/* Collection Selector */}
          <div className="p-3 border-b border-gray-100">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5 px-1">
              Study Context
            </label>
            <div className="relative">
              <select
                value={selectedCol}
                onChange={(e) => setSelectedCol(Number(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:bg-white transition-all cursor-pointer"
              >
                {collections.length === 0 && <option value={0}>General Study</option>}
                {collections.map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Single New Chat Button */}
          <div className="p-3 border-b border-gray-100">
            <button
              onClick={handleStartNewChat}
              className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-sm font-medium shadow-sm transition-all"
            >
              <Plus className="w-4 h-4" /> New Chat
            </button>
          </div>

          {/* Conversations History List */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
            <div className="px-2 py-1 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              Recent Chats
            </div>
            {sessions.map((s: any) => {
              const isActive = activeSession === s.id;
              return (
                <div
                  key={s.id}
                  onClick={() => setActiveSession(s.id)}
                  className={`group w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm transition-all cursor-pointer ${
                    isActive
                      ? 'bg-purple-50 text-purple-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate mr-2">
                    <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? 'text-purple-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
                    <span className="truncate">{s.title || 'Untitled Conversation'}</span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    title="Delete Chat"
                    className="opacity-0 group-hover:opacity-100 hover:text-red-600 text-gray-400 p-1 rounded-md hover:bg-red-50 transition-all flex-shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
            {sessions.length === 0 && (
              <div className="text-center py-10 px-4">
                <MessageSquare className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-xs text-gray-400">No previous conversations yet.</p>
                <p className="text-[11px] text-gray-400 mt-1">Send a message to start one!</p>
              </div>
            )}
          </div>
        </div>

        {/* Main Chat Area - Always Open, Active & Ready to Type Immediately */}
        <div className="flex-1 bg-white rounded-2xl border border-gray-100 flex flex-col shadow-sm overflow-hidden">
          {/* Header */}
          <div className="px-6 py-3 border-b border-gray-100 flex items-center justify-between bg-white">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span className="text-sm font-semibold text-gray-800">
                {activeSessionTitle ? activeSessionTitle : 'New Conversation'}
              </span>
              {selectedCol > 0 && (
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-md">
                  {collections.find((c) => c.id === selectedCol)?.name || 'Study Collection'}
                </span>
              )}
            </div>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto py-10">
                <div className="w-14 h-14 bg-gradient-to-tr from-purple-100 to-indigo-100 rounded-2xl flex items-center justify-center mb-4 shadow-sm border border-purple-100">
                  <Sparkles className="w-7 h-7 text-purple-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-2">How can Source2Study help you today?</h2>
                <p className="text-gray-500 text-sm mb-8 leading-relaxed max-w-md">
                  Ask questions about your uploaded study materials, analyze past papers, or generate practice questions.
                </p>

                {/* Prompt Suggestions */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full text-left">
                  {suggestedPrompts.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => sendMessage(p)}
                      className="p-3.5 bg-gray-50 hover:bg-purple-50/70 border border-gray-100 hover:border-purple-200 rounded-xl text-xs text-gray-700 hover:text-purple-700 transition-all text-left flex items-start gap-2 group"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-purple-500 mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform" />
                      <span className="font-medium leading-relaxed">{p}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m: any) => {
                const isUser = m.role === 'user';
                return (
                  <div key={m.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[82%] ${
                        isUser
                          ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl rounded-br-md px-5 py-3 shadow-sm'
                          : 'bg-gray-50 text-gray-800 rounded-2xl rounded-bl-md px-5 py-3.5 border border-gray-100 shadow-sm'
                      }`}
                    >
                      {isUser ? (
                        <div className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</div>
                      ) : (
                        <MarkdownRenderer content={m.content} className="text-sm" />
                      )}

                      {/* Source citations */}
                      {m.sources_json && m.sources_json.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-gray-200/60">
                          <p className="text-xs font-semibold opacity-75 mb-1.5 flex items-center gap-1">
                            <BookOpen className="w-3 h-3" /> Cited Sources:
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {m.sources_json.map((s: any, i: number) => (
                              <span
                                key={i}
                                className={`text-[11px] rounded-md px-2 py-0.5 font-medium ${
                                  isUser ? 'bg-white/20 text-white' : 'bg-purple-100/70 text-purple-800 border border-purple-200/50'
                                }`}
                              >
                                {s.filename} {s.page_number ? `(p. ${s.page_number})` : ''}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {!isUser && (
                        <div className="mt-2.5 flex items-center justify-between text-xs text-gray-400 pt-1">
                          <button
                            onClick={() => copyText(m.content, m.id)}
                            className="flex items-center gap-1 hover:text-purple-600 transition-colors"
                          >
                            {copied === m.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-500" />
                                <span className="text-emerald-600">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy response</span>
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {sending && (
              <div className="flex justify-start">
                <div className="bg-gray-50 rounded-2xl rounded-bl-md px-5 py-3.5 border border-gray-100 shadow-sm">
                  <div className="flex items-center gap-2.5 text-xs font-medium text-gray-500">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span>Source2Study AI is searching resources and thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Active Message Input Box - Always Displayed & Enabled Immediately */}
          <div className="p-4 border-t border-gray-100 bg-white">
            <div className="flex items-center gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                disabled={sending}
                placeholder="Ask about your study materials, formulas, questions..."
                className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:bg-white transition-all disabled:opacity-50"
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || sending}
                className="px-5 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl disabled:opacity-40 hover:from-purple-700 hover:to-indigo-700 transition-all font-medium text-sm flex items-center gap-1.5 shadow-sm"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </div>
            <p className="text-[11px] text-gray-400 mt-2 text-center">
              Source2Study AI searches your uploaded materials to provide cited answers. Press Enter to send.
            </p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
