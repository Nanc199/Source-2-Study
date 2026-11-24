'use client';
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  if (!content) return null;

  return (
    <div className={`prose-academic text-gray-800 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ node, ...props }) => (
            <h1 className="text-xl font-bold text-gray-900 mt-5 mb-2.5 pb-1.5 border-b border-gray-100 flex items-center gap-2" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-lg font-bold text-purple-900 mt-4 mb-2 flex items-center gap-2" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-base font-semibold text-gray-900 mt-3 mb-1.5" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-sm font-semibold text-gray-800 mt-2 mb-1" {...props} />
          ),
          p: ({ node, ...props }) => (
            <p className="text-sm text-gray-700 leading-relaxed mb-3 last:mb-0" {...props} />
          ),
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-outside pl-5 space-y-1.5 text-sm text-gray-700 mb-3" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-outside pl-5 space-y-1.5 text-sm text-gray-700 mb-3" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="leading-relaxed pl-1" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong className="font-bold text-gray-900 bg-purple-50/60 px-1 py-0.5 rounded text-[13px]" {...props} />
          ),
          em: ({ node, ...props }) => (
            <em className="italic text-gray-800" {...props} />
          ),
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-4 border-purple-500 pl-4 py-2 my-3 bg-purple-50/40 rounded-r-xl text-sm text-purple-950 italic" {...props} />
          ),
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-4 border border-gray-200 rounded-xl shadow-sm bg-white">
              <table className="min-w-full divide-y divide-gray-200 text-sm text-left" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-gray-50 text-gray-800 font-semibold text-xs uppercase tracking-wider" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody className="divide-y divide-gray-100 bg-white" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="px-4 py-2.5 font-bold text-gray-900 border-b border-gray-200" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="px-4 py-2.5 text-gray-700 border-b border-gray-50" {...props} />
          ),
          code: ({ node, inline, className: codeClass, children, ...props }: any) => {
            if (inline) {
              return (
                <code className="bg-gray-100 text-purple-700 px-1.5 py-0.5 rounded text-xs font-mono font-medium" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <div className="my-3 overflow-x-auto rounded-xl bg-gray-900 text-gray-100 p-4 font-mono text-xs shadow-inner">
                <code {...props}>{children}</code>
              </div>
            );
          },
          hr: ({ node, ...props }) => (
            <hr className="my-4 border-gray-200" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
