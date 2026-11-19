'use client';
import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { collectionsApi, chatApi } from '@/lib/api';
import { Send, Plus, MessageSquare, Trash2, BookOpen, Sparkles, Copy, Check } from 'lucide-react';

export default function ChatPage() {
  const searchParams = useSearchParams();
  const presetCol = searchParams.get('collection');
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<number>(0);
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<number | null>(null);
  const [isNewChat, setIsNewChat] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    collectionsApi.list().then((c: any[]) => {
      setCollections(c);
      if (presetCol) setSelectedCol(Number(presetCol));
      else if (c.length > 0) setSelectedCol(c[0].id);
    });
  }, [presetCol]);

  useEffect(() => {
    if (!selectedCol) return;
    chatApi.listSessions(selectedCol).then(setSessions).catch(() => setSessions([]));
    setActiveSession(null);
    setIsNewChat(false);
    setMessages([]);
  }, [selectedCol]);

  useEffect(() => {
    if (!activeSession) return;
    chatApi.getMessages(activeSession).then(setMessages).catch(() => {});
  }, [activeSession]);

  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const createSession = () => {
    if (!selectedCol) return;
    // Keep a single unsaved New Chat draft; persist it when the first message is sent.
    setActiveSession(null);
    setIsNewChat(true);
    setMessages([]);
  };

  const sendMessage = async () => {
    if (!input.trim() || (!activeSession && !isNewChat) || sending) return;
    const content = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { id: Date.now(), role: 'user', content, created_at: new Date().toISOString() }]);
    setSending(true);
    try {
      let sessionId: number;
      if (activeSession) {
        sessionId = activeSession;
      } else {
        const session = await chatApi.createSession(selectedCol, content.slice(0, 100));
        sessionId = session.id;
        setActiveSession(session.id);
        setIsNewChat(false);
        setSessions((prev) => [session, ...prev]);
      }
      const resp = await chatApi.sendMessage(sessionId, content);
      setSessions((prev) => prev.map((session) => session.id === sessionId
        ? { ...session, title: session.title === 'New Chat' ? content.slice(0, 100) : session.title, message_count: (session.message_count || 0) + 2 }
        : session));
      setMessages((prev) => [...prev, resp]);
    } catch (e: any) {
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: 'assistant', content: `Error: ${e.message}`, created_at: new Date().toISOString() }]);
    } finally {
      setSending(false);
    }
  };

  const copyText = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const suggestedPrompts = [
    'Summarize all uploaded documents',
    'Explain the key concepts',
    'Generate important questions from the material',
    'Compare and contrast the main topics',
  ];

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-7rem)] gap-4">
        {/* Sidebar */}
        <div className="w-72 bg-white rounded-2xl border border-gray-100 flex flex-col flex-shrink-0">
          <div className="p-4 border-b border-gray-100">
            <select value={selectedCol} onChange={(e) => setSelectedCol(Number(e.target.value))}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
              <option value={0}>Select Collection</option>
              {collections.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="p-3">
              <button onClick={createSession} disabled={!selectedCol}
              className="w-full flex items-center gap-2 px-3 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-medium disabled:opacity-50">
              <Plus className="w-4 h-4" /> New Chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-1">
            {sessions.map((s: any) => (
              <button key={s.id} onClick={() => { setActiveSession(s.id); }}
                className={`w-full text-left px-3 py-2.5 rounded-xl text-sm truncate transition-colors ${
                  activeSession === s.id ? 'bg-purple-50 text-purple-700 font-medium' : 'text-gray-600 hover:bg-gray-50'
                }`}>
                <MessageSquare className="w-3.5 h-3.5 inline mr-2 opacity-50" />
                {s.title || 'New Chat'}
              </button>
            ))}
            {sessions.length === 0 && selectedCol > 0 && (
              <p className="text-xs text-gray-400 text-center py-8">No chats yet. Start a new one!</p>
            )}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 bg-white rounded-2xl border border-gray-100 flex flex-col">
          {!activeSession && !isNewChat ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8">
              <div className="w-16 h-16 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-2xl flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-purple-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">AI Study Assistant</h2>
              <p className="text-gray-500 text-sm text-center max-w-md mb-8">Ask questions about your uploaded study materials. The AI will search through your documents and provide sourced answers.</p>
              {selectedCol > 0 && (
                <button onClick={createSession} className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-sm font-medium shadow-lg shadow-purple-200">
                  Start New Chat
                </button>
              )}
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center py-12">
                    <p className="text-gray-400 text-sm mb-6">Start by asking a question about your study materials</p>
                    <div className="grid grid-cols-2 gap-2 max-w-lg mx-auto">
                      {suggestedPrompts.map((p) => (
                        <button key={p} onClick={() => { setInput(p); }}
                          className="text-left px-4 py-3 bg-gray-50 hover:bg-purple-50 border border-gray-100 hover:border-purple-200 rounded-xl text-sm text-gray-600 hover:text-purple-700 transition-colors">
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {messages.map((m: any) => (
                  <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] ${m.role === 'user'
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl rounded-br-md px-5 py-3'
                      : 'bg-gray-50 text-gray-800 rounded-2xl rounded-bl-md px-5 py-3 border border-gray-100'}`}>
                      <div className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</div>
                      {m.sources_json && m.sources_json.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-gray-200/50">
                          <p className="text-xs font-medium opacity-70 mb-1">📄 Sources:</p>
                          {m.sources_json.map((s: any, i: number) => (
                            <span key={i} className="inline-block text-xs bg-white/20 rounded px-2 py-0.5 mr-1 mb-1">
                              {s.filename} {s.page_number ? `(p.${s.page_number})` : ''}
                            </span>
                          ))}
                        </div>
                      )}
                      {m.role === 'assistant' && (
                        <button onClick={() => copyText(m.content, m.id)} className="mt-2 text-xs opacity-50 hover:opacity-100 flex items-center gap-1">
                          {copied === m.id ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {sending && (
                  <div className="flex justify-start">
                    <div className="bg-gray-50 rounded-2xl rounded-bl-md px-5 py-4 border border-gray-100">
                      <div className="flex items-center gap-2 text-sm text-gray-400">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                        Thinking...
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEnd} />
              </div>

              {/* Input */}
              <div className="p-4 border-t border-gray-100">
                <div className="flex gap-3">
                  <input type="text" value={input} onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                    disabled={!activeSession && !isNewChat}
                    placeholder="Ask about your study materials..."
                    className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:bg-white" />
                  <button onClick={sendMessage} disabled={!input.trim() || sending}
                    className="px-4 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl disabled:opacity-50 hover:from-purple-700 hover:to-indigo-700">
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
