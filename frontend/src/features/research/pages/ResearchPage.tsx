import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom';
import { FileText, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import { Message } from '../components/Message';
import { QuestionInput } from '../components/QuestionInput';
import { SourcePanel } from '../components/SourcePanel';
import { apiClient } from '../../../api/client';
import type { ChatMessage, Citation, Chat, Document } from '../../../types';

export function ResearchPage() {
  const { chatId: chatIdParam } = useParams<{ chatId?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const documentIdParam = searchParams.get('documentId');
  const parsedDocId = documentIdParam ? parseInt(documentIdParam, 10) : null;
  const parsedChatId = chatIdParam ? parseInt(chatIdParam, 10) : null;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatId, setChatId] = useState<number | null>(parsedChatId);
  const [document, setDocument] = useState<Document | null>(null);
  const [isDocUnavailable, setIsDocUnavailable] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Resolution & Data Loading Effect
  useEffect(() => {
    let isCancelled = false;

    // Case 1: Active persistent chatId in URL
    if (parsedChatId) {
      setChatId(parsedChatId);
      setIsLoadingHistory(true);
      setError(null);

      Promise.all([
        apiClient<Chat>(`/api/v1/chats/${parsedChatId}`),
        apiClient<ChatMessage[]>(`/api/v1/chats/${parsedChatId}/messages`),
      ])
        .then(([chatData, chatMessages]) => {
          if (isCancelled) return;

          setMessages(
            chatMessages.map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              citations: m.citations || [],
              createdAt: m.createdAt,
            }))
          );

          // Resolve document context from chat documents
          if (chatData.documents && chatData.documents.length > 0) {
            const primaryDoc = chatData.documents[0];
            if (primaryDoc.isDeleted) {
              setIsDocUnavailable(true);
              setDocument({
                ...primaryDoc,
                fileType: 'UNAVAILABLE',
                documentType: 'Document removed or inaccessible',
                status: 'FAILED',
              });
            } else {
              setIsDocUnavailable(false);
              setDocument(primaryDoc);
            }
          } else if (parsedDocId) {
            // Fallback fetch if document was not pre-populated in chat documents
            apiClient<Document>(`/api/v1/documents/${parsedDocId}`)
              .then((doc) => {
                if (isCancelled) return;
                setDocument(doc);
                setIsDocUnavailable(false);
              })
              .catch(() => {
                if (isCancelled) return;
                setIsDocUnavailable(true);
                setDocument({
                  id: parsedDocId,
                  fileName: `Document #${parsedDocId}`,
                  fileType: 'UNAVAILABLE',
                  documentType: 'Document removed or inaccessible',
                  status: 'FAILED',
                  uploadedAt: '',
                });
              });
          } else {
            setDocument(null);
            setIsDocUnavailable(false);
          }
        })
        .catch((err) => {
          if (isCancelled) return;
          console.error('Failed to load chat history:', err);
          setError(err.message || 'Chat not found or access denied.');
          setMessages([]);
        })
        .finally(() => {
          if (!isCancelled) {
            setIsLoadingHistory(false);
          }
        });

      return () => {
        isCancelled = true;
      };
    }

    // Case 2: Document ID supplied without chatId -> Resolve or create persistent chat
    if (parsedDocId && !parsedChatId) {
      setIsLoadingHistory(true);
      setError(null);

      apiClient<Chat>(`/api/v1/chats/document/${parsedDocId}`)
        .then((chat) => {
          if (isCancelled) return;
          // Transition URL to persistent /research/:chatId?documentId=...
          navigate(`/research/${chat.id}?documentId=${parsedDocId}`, { replace: true });
        })
        .catch((err) => {
          if (isCancelled) return;
          console.error('Failed to resolve chat for document:', err);
          setError(err.message || 'Document not found or access denied.');
          setIsLoadingHistory(false);
        });

      return () => {
        isCancelled = true;
      };
    }

    // Case 3: No document and no chatId selected
    setChatId(null);
    setDocument(null);
    setMessages([]);
    setIsDocUnavailable(false);
    setIsLoadingHistory(false);
    setError(null);
  }, [parsedChatId, parsedDocId, navigate]);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleAsk = async (question: string) => {
    if (!question.trim() || !chatId || isLoading) return;

    const now = new Date();
    const userMessage: ChatMessage = {
      id: Date.now(),
      role: 'USER',
      content: question,
      citations: [],
      createdAt: now.toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const payload: { content: string; documentIds?: number[] } = {
        content: question,
      };

      if (parsedDocId && messages.length === 0) {
        payload.documentIds = [parsedDocId];
      }

      const response = await apiClient<{
        id: number;
        role: 'USER' | 'ASSISTANT';
        content: string;
        citations: Citation[];
        createdAt: string;
      }>(`/api/v1/chats/${chatId}/messages`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const assistantMessage: ChatMessage = {
        id: response.id || Date.now() + 1,
        role: 'ASSISTANT',
        content: response.content,
        citations: response.citations || [],
        createdAt: response.createdAt || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('Failed to ask question:', err);
      setError(err.message || 'Failed to receive answer from backend.');
    } finally {
      setIsLoading(false);
    }
  };

  const allCitations = messages.flatMap((m) => m.citations || []);

  const formatTime = (isoString?: string) => {
    if (!isoString) return '';
    try {
      return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const hasSelectedContext = parsedChatId || parsedDocId || document;

  return (
    <div className="flex h-full">
      {/* Center Conversation Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Research Header */}
        <div className="p-8 border-b border-penny-border dark:border-penny-dark-border">
          <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-3">
            Research
          </div>
          {hasSelectedContext ? (
            <>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-medium tracking-tight uppercase">
                  {document?.fileName || (parsedDocId ? `Document #${parsedDocId}` : 'Financial Research')}
                </h1>
                {isDocUnavailable && (
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 border border-penny-accent/40 text-penny-accent dark:text-penny-dark-accent bg-penny-accent/5">
                    Unavailable
                  </span>
                )}
              </div>
              <div className="text-lg text-[#666666] dark:text-[#999999] mb-3">
                {isDocUnavailable
                  ? 'Source document is no longer available'
                  : document?.documentType || 'Financial Filing'}
              </div>
              <div className="flex gap-4 text-xs text-[#666666] dark:text-[#999999]">
                <span>Status: {isDocUnavailable ? 'UNAVAILABLE' : document?.status || 'READY'}</span>
                <span>•</span>
                <span>{document?.fileType || 'PDF'}</span>
                {document?.uploadedAt && (
                  <>
                    <span>•</span>
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
            </>
          ) : (
            <>
              <h1 className="text-2xl font-medium tracking-tight">Select a Document</h1>
              <div className="text-sm text-[#666666] dark:text-[#999999] mt-1">
                Choose a document from your library to start grounded financial research.
              </div>
            </>
          )}
        </div>

        {/* Conversation History */}
        {!hasSelectedContext ? (
          <div className="flex-1 p-8 flex flex-col items-center justify-center text-center">
            <FileText size={48} strokeWidth={1} className="text-[#DCDCD7] dark:text-[#303030] mb-6" />
            <h3 className="text-lg font-medium mb-2">No document selected</h3>
            <p className="text-sm text-[#666666] dark:text-[#999999] mb-6 max-w-xs">
              Select a document to begin verified financial research with deterministic reasoning and page citations.
            </p>
            <Link
              to="/documents"
              className="inline-flex items-center gap-2 bg-penny-text dark:bg-penny-dark-text text-penny-bg dark:text-penny-dark-bg px-6 py-3 text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Browse Documents <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <div className="flex-1 p-8 overflow-y-auto flex flex-col gap-8">
            {isLoadingHistory && (
              <div className="flex-1 flex flex-col items-center justify-center text-center py-16 text-[#666666] dark:text-[#999999]">
                <Loader2 size={20} className="animate-spin text-penny-accent dark:text-penny-dark-accent mb-3" />
                <div className="text-xs uppercase tracking-widest font-mono">Loading conversation...</div>
              </div>
            )}

            {!isLoadingHistory && messages.length === 0 && !isLoading && !error && (
              <div className="flex-1 flex flex-col items-center justify-center text-center py-12 text-[#666666] dark:text-[#999999]">
                <div className="text-xs uppercase tracking-widest font-semibold mb-2">
                  {isDocUnavailable ? 'Document Removed' : 'Ready for Research'}
                </div>
                <p className="text-xs max-w-sm">
                  {isDocUnavailable
                    ? 'The source document for this research has been removed. Previous messages remain visible.'
                    : `Ask a question below to analyze ${document?.fileName || 'this document'} with deterministic calculations and page citations.`}
                </p>
              </div>
            )}

            {!isLoadingHistory &&
              messages.map((msg, idx) => (
                <React.Fragment key={msg.id || idx}>
                  {idx > 0 && (
                    <hr className="border-t border-penny-border dark:border-penny-dark-border" />
                  )}
                  <Message
                    role={msg.role}
                    time={formatTime(msg.createdAt)}
                    content={msg.content}
                    citations={msg.citations}
                  />
                </React.Fragment>
              ))}

            {isLoading && (
              <>
                {messages.length > 0 && (
                  <hr className="border-t border-penny-border dark:border-penny-dark-border" />
                )}
                <div className="flex flex-col gap-3">
                  <div className="flex justify-between items-baseline">
                    <span className="text-[10px] uppercase tracking-widest font-semibold text-penny-accent dark:text-penny-dark-accent">
                      Penny
                    </span>
                    <span className="text-[10px] text-[#666666] dark:text-[#999999]">Processing...</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-[#666666] dark:text-[#999999]">
                    <Loader2 size={16} className="animate-spin text-penny-accent dark:text-penny-dark-accent" />
                    <span>Analyzing document context and calculating answer...</span>
                  </div>
                </div>
              </>
            )}

            {error && (
              <div className="p-4 border border-penny-accent/40 bg-penny-accent/5 text-penny-accent dark:text-penny-dark-accent flex items-start gap-3 text-xs">
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold uppercase tracking-wider mb-0.5">Error</div>
                  <div>{error}</div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        <QuestionInput
          onAsk={handleAsk}
          isLoading={isLoading}
          disabled={!hasSelectedContext || isDocUnavailable || !chatId}
          placeholder={
            !hasSelectedContext
              ? 'Select a document first to ask questions...'
              : isDocUnavailable
              ? 'Source document is no longer available.'
              : 'Ask a question about this document...'
          }
        />
      </div>

      {/* Right Sidebar */}
      <SourcePanel citations={allCitations} document={document} />
    </div>
  );
}