import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, ArrowRight, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { apiClient } from '../../../api/client';
import type { Document } from '../../../types';

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('Overview');
  const [document, setDocument] = useState<Document | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const tabs = ['Overview', 'Document', 'Key Facts'];

  useEffect(() => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    apiClient<Document>(`/api/v1/documents/${id}`)
      .then((doc) => {
        setDocument(doc);
      })
      .catch((err) => {
        console.warn('Could not fetch document:', err);
        setError('Document not found or access denied.');
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center gap-3 text-xs text-[#666666] dark:text-[#999999]">
        <Loader2 size={16} className="animate-spin text-penny-accent dark:text-penny-dark-accent" />
        <span>Loading document...</span>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="max-w-2xl mx-auto p-12 text-center flex flex-col items-center justify-center h-full">
        <FileText size={48} strokeWidth={1} className="text-[#DCDCD7] dark:text-[#303030] mb-4" />
        <h2 className="text-xl font-medium mb-2">Document Unavailable</h2>
        <p className="text-xs text-[#666666] dark:text-[#999999] mb-6 max-w-sm">
          {error || 'This document could not be found or you do not have permission to view it.'}
        </p>
        <Link
          to="/documents"
          className="inline-flex items-center gap-2 bg-penny-text dark:bg-penny-dark-text text-penny-bg dark:text-penny-dark-bg px-6 py-3 text-xs font-medium hover:opacity-90 transition-opacity"
        >
          <ArrowLeft size={14} /> Return to Documents
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-8">
          {/* Back link */}
          <Link
            to="/documents"
            className="inline-flex items-center gap-2 text-xs text-[#666666] dark:text-[#999999] hover:text-penny-text dark:hover:text-penny-dark-text mb-8 transition-colors"
          >
            <ArrowLeft size={14} /> Back to documents
          </Link>

          {/* Title */}
          <h1 className="text-3xl font-medium tracking-tight uppercase">{document.fileName}</h1>
          <div className="text-lg text-[#666666] dark:text-[#999999] mb-4">
            {document.documentType || `${document.fileType} Document`}
          </div>
          <div className="flex items-center gap-4 text-xs text-[#666666] dark:text-[#999999] mb-8">
            <span>Status: {document.status}</span>
            <span className="opacity-40">|</span>
            <span>{document.fileType}</span>
            {document.uploadedAt && (
              <>
                <span className="opacity-40">|</span>
                <span>
                  Filed{' '}
                  {new Date(document.uploadedAt).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </span>
              </>
            )}
          </div>

          {/* Tabs */}
          <div className="flex gap-8 border-b border-penny-border dark:border-penny-dark-border mb-10">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-3 text-xs font-medium transition-colors ${
                  activeTab === tab
                    ? 'border-b-2 border-penny-text dark:border-penny-dark-text text-penny-text dark:text-penny-dark-text'
                    : 'text-[#666666] dark:text-[#999999] hover:text-penny-text dark:hover:text-penny-dark-text'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Overview Empty State */}
        {activeTab === 'Overview' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8 pb-16">
            <FileText size={48} strokeWidth={1} className="text-[#DCDCD7] dark:text-[#303030] mb-6" />
            <h3 className="text-lg font-medium mb-2">Verified Document Summary</h3>
            <p className="text-sm text-[#666666] dark:text-[#999999] mb-6 max-w-xs">
              Use Research to ask questions or extract key financial tables with citations.
            </p>
            <Link
              to={`/research?documentId=${document.id}`}
              className="inline-flex items-center gap-2 bg-penny-text dark:bg-penny-dark-text text-penny-bg dark:text-penny-dark-bg px-6 py-3 text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Go to Research <ArrowRight size={16} />
            </Link>
          </div>
        )}

        {activeTab === 'Document' && (
          <div className="flex-1 flex items-center justify-center text-sm text-[#666666] dark:text-[#999999]">
            Document viewer coming soon
          </div>
        )}

        {activeTab === 'Key Facts' && (
          <div className="flex-1 flex items-center justify-center text-sm text-[#666666] dark:text-[#999999]">
            Key facts coming soon
          </div>
        )}
      </div>

        {/* Research Sidebar */}
      <aside className="w-80 border-l border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface flex flex-col">
        <div className="p-6 border-b border-penny-border dark:border-penny-dark-border">
          <h2 className="text-[10px] uppercase tracking-widest font-semibold">Live Research</h2>
        </div>

        <div className="flex-1 p-6 flex flex-col items-center justify-center text-center">
          <FileText size={36} strokeWidth={1} className="text-[#DCDCD7] dark:text-[#303030] mb-4" />
          <h3 className="text-sm font-medium mb-2">Ask Questions with AI</h3>
          <p className="text-xs text-[#666666] dark:text-[#999999] mb-6 max-w-xs">
            Start a grounded research session with deterministic financial calculations and page citations.
          </p>
          <Link
            to={`/research?documentId=${document.id}`}
            className="inline-flex items-center gap-2 bg-penny-text dark:bg-penny-dark-text text-penny-bg dark:text-penny-dark-bg px-5 py-2.5 text-xs font-medium hover:opacity-90 transition-opacity"
          >
            Open Research <ArrowRight size={14} />
          </Link>
        </div>
      </aside>
    </div>
  );
}
