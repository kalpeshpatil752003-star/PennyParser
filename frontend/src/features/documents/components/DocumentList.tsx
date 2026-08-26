import { useState, useEffect, useRef } from 'react';
import {
  FileText,
  ArrowRight,
  MoreVertical,
  Trash2,
  BarChart3,
  MessageSquare,
  Loader2,
  CheckCircle2,
  X,
  AlertTriangle,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { apiClient } from '../../../api/client';
import type { Document } from '../../../types';

interface DisplayDoc {
  id: number;
  name: string;
  subtitle: string;
  status: string;
  date: string;
}

interface DocumentListProps {
  refreshKey?: number;
}

export function DocumentList({ refreshKey }: DocumentListProps) {
  const [documents, setDocuments] = useState<DisplayDoc[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [docToDelete, setDocToDelete] = useState<DisplayDoc | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const fetchDocuments = () => {
    setIsLoading(true);
    apiClient<Document[]>('/api/v1/documents')
      .then((docs) => {
        if (Array.isArray(docs)) {
          const mapped: DisplayDoc[] = docs.map((d) => ({
            id: d.id,
            name: d.fileName.replace(/\.[^/.]+$/, ''),
            subtitle: d.documentType || `${d.fileType} Document`,
            status: d.status,
            date: d.uploadedAt
              ? new Date(d.uploadedAt).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })
              : 'Recent',
          }));
          setDocuments(mapped);
        } else {
          setDocuments([]);
        }
      })
      .catch((err) => {
        console.warn('Could not fetch documents:', err);
        setDocuments([]);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchDocuments();
  }, [refreshKey]);

  // Close contextual menu when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenId(null);
      }
    }
    if (menuOpenId !== null) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [menuOpenId]);

  // Handle ESC key to dismiss dialog or menu
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (docToDelete && !isDeleting) {
          setDocToDelete(null);
        }
        setMenuOpenId(null);
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [docToDelete, isDeleting]);

  const handleDeleteConfirm = async () => {
    if (!docToDelete || isDeleting) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      // Execute real backend deletion
      await apiClient<void>(`/api/v1/documents/${docToDelete.id}`, {
        method: 'DELETE',
      });

      // Remove from local state immediately
      const deletedId = docToDelete.id;
      const deletedName = docToDelete.name;
      setDocuments((prev) => prev.filter((d) => d.id !== deletedId));

      // Show minimal success feedback
      setSuccessMessage(`Document "${deletedName}" and its financial data were deleted.`);
      setDocToDelete(null);

      // Auto-dismiss success notification
      setTimeout(() => {
        setSuccessMessage(null);
      }, 4000);

      // Invalidate / refetch list from backend
      fetchDocuments();
    } catch (err: any) {
      console.error('Failed to delete document:', err);
      setDeleteError(err.message || 'Failed to delete document on server.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="mt-16">
      {/* Minimal Success Notification */}
      {successMessage && (
        <div className="mb-6 border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-4 flex items-center justify-between text-xs transition-all">
          <div className="flex items-center gap-3 text-penny-text dark:text-penny-dark-text">
            <CheckCircle2 size={15} className="text-penny-accent dark:text-penny-dark-accent" />
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage(null)}
            className="text-[#666666] dark:text-[#999999] hover:text-penny-text dark:hover:text-penny-dark-text p-1 cursor-pointer"
            aria-label="Dismiss message"
          >
            <X size={14} />
          </button>
        </div>
      )}

      <h2 className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-6">
        Recent Documents
      </h2>

      {isLoading ? (
        <div className="py-12 border-t border-b border-penny-border dark:border-penny-dark-border flex items-center justify-center gap-3 text-xs text-[#666666] dark:text-[#999999]">
          <Loader2 size={16} className="animate-spin text-penny-accent dark:text-penny-dark-accent" />
          <span>Loading documents...</span>
        </div>
      ) : documents.length === 0 ? (
        <div className="py-16 border-t border-b border-penny-border dark:border-penny-dark-border text-center flex flex-col items-center justify-center">
          <FileText size={32} strokeWidth={1} className="text-[#DCDCD7] dark:text-[#303030] mb-3" />
          <h3 className="text-sm font-medium mb-1">No documents in your library</h3>
          <p className="text-xs text-[#666666] dark:text-[#999999] max-w-xs">
            Upload a PDF, DOCX, or TXT document above to start verified financial research with deterministic reasoning.
          </p>
        </div>
      ) : (
        <div className="flex flex-col border-t border-penny-border dark:border-penny-dark-border">
          {documents.map((doc) => (
          <div
            key={doc.id}
            className="group flex items-center justify-between py-5 border-b border-penny-border dark:border-penny-dark-border hover:bg-penny-surface dark:hover:bg-penny-dark-surface transition-colors px-4 -mx-4"
          >
            <Link
              to={`/research?documentId=${doc.id}`}
              className="flex-1 flex items-center gap-5 min-w-0 cursor-pointer"
            >
              <FileText size={18} strokeWidth={1.5} className="text-[#666666] dark:text-[#999999] shrink-0" />
              <div className="min-w-0">
                <h3 className="text-sm font-medium truncate">{doc.name}</h3>
                <div className="text-xs text-[#666666] dark:text-[#999999] mt-0.5 flex gap-3 truncate">
                  <span>{doc.subtitle}</span>
                  <span className="opacity-50">|</span>
                  <span>{doc.date}</span>
                </div>
              </div>
            </Link>

            <div className="flex items-center gap-4 shrink-0 pl-4">
              <span
                className={`text-[10px] uppercase tracking-widest font-mono ${
                  doc.status === 'PROCESSING' ||
                  doc.status === 'EXTRACTING' ||
                  doc.status === 'CHUNKING' ||
                  doc.status === 'EMBEDDING'
                    ? 'text-penny-accent dark:text-penny-dark-accent animate-pulse'
                    : 'text-[#666666] dark:text-[#999999]'
                }`}
              >
                {doc.status}
              </span>

              <Link
                to={`/research?documentId=${doc.id}`}
                className="opacity-0 group-hover:opacity-100 text-penny-accent dark:text-penny-dark-accent transition-opacity p-1"
                title="Go to Research"
              >
                <ArrowRight size={16} />
              </Link>

              {/* Three-Dot Contextual Menu */}
              <div className="relative" ref={menuOpenId === doc.id ? menuRef : null}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setMenuOpenId(menuOpenId === doc.id ? null : doc.id);
                  }}
                  className="p-1.5 text-[#666666] dark:text-[#999999] hover:text-penny-text dark:hover:text-penny-dark-text hover:bg-penny-border/30 dark:hover:bg-penny-dark-border/40 transition-colors cursor-pointer"
                  aria-label="Document actions"
                  title="Document actions"
                >
                  <MoreVertical size={16} />
                </button>

                {menuOpenId === doc.id && (
                  <div
                    className="absolute right-0 top-full mt-1 w-44 bg-penny-surface dark:bg-penny-dark-surface border border-penny-border dark:border-penny-dark-border shadow-md z-40 py-1"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setMenuOpenId(null);
                        navigate(`/documents/${doc.id}`);
                      }}
                      className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-left text-penny-text dark:text-penny-dark-text hover:bg-penny-bg dark:hover:bg-penny-dark-bg transition-colors cursor-pointer"
                    >
                      <FileText size={13} className="text-[#666666] dark:text-[#999999]" />
                      <span>Open</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setMenuOpenId(null);
                        navigate(`/research?documentId=${doc.id}`);
                      }}
                      className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-left text-penny-text dark:text-penny-dark-text hover:bg-penny-bg dark:hover:bg-penny-dark-bg transition-colors cursor-pointer"
                    >
                      <MessageSquare size={13} className="text-[#666666] dark:text-[#999999]" />
                      <span>Research</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setMenuOpenId(null);
                        navigate(`/analysis?documentId=${doc.id}`);
                      }}
                      className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-left text-penny-text dark:text-penny-dark-text hover:bg-penny-bg dark:hover:bg-penny-dark-bg transition-colors cursor-pointer"
                    >
                      <BarChart3 size={13} className="text-[#666666] dark:text-[#999999]" />
                      <span>Analysis</span>
                    </button>

                    <div className="border-t border-penny-border dark:border-penny-dark-border my-1" />

                    <button
                      type="button"
                      onClick={() => {
                        setMenuOpenId(null);
                        setDeleteError(null);
                        setDocToDelete(doc);
                      }}
                      className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-left text-penny-accent dark:text-penny-dark-accent hover:bg-penny-accent/10 transition-colors cursor-pointer"
                    >
                      <Trash2 size={13} />
                      <span>Delete</span>
                    </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Minimal Confirmation Dialog */}
      {docToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-100">
          <div
            className="w-full max-w-md bg-penny-surface dark:bg-penny-dark-surface border border-penny-border dark:border-penny-dark-border p-6 shadow-xl flex flex-col gap-5"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
          >
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest font-semibold text-penny-accent dark:text-penny-dark-accent">
                <AlertTriangle size={13} />
                <span>Confirm Deletion</span>
              </div>
              <h3
                id="delete-dialog-title"
                className="text-base font-medium tracking-tight text-penny-text dark:text-penny-dark-text"
              >
                {docToDelete.name}
              </h3>
            </div>

            <div className="text-xs text-[#666666] dark:text-[#999999] leading-relaxed">
              This document and its associated financial data, extracted tables, and AI vectors will
              be permanently removed.
            </div>

            <div className="text-[11px] text-[#666666] dark:text-[#999999] border-l-2 border-penny-border dark:border-penny-dark-border pl-3 py-1 bg-penny-bg dark:bg-penny-dark-bg">
              Existing research chats will remain accessible, but will no longer have access to this
              document for future queries.
            </div>

            {deleteError && (
              <div className="text-xs text-penny-accent dark:text-penny-dark-accent border border-penny-accent/30 bg-penny-accent/5 p-3">
                {deleteError}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-penny-border dark:border-penny-dark-border">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setDocToDelete(null)}
                className="px-4 py-2 text-xs font-medium border border-penny-border dark:border-penny-dark-border hover:bg-penny-bg dark:hover:bg-penny-dark-bg transition-colors disabled:opacity-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={handleDeleteConfirm}
                className="px-4 py-2 text-xs font-medium bg-penny-accent text-white hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2 cursor-pointer"
              >
                {isDeleting ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <span>Delete Document</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}