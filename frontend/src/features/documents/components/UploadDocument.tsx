import React, { useState, useRef } from 'react';
import { Plus, Loader2, AlertCircle } from 'lucide-react';
import { apiClient } from '../../../api/client';
import type { Document } from '../../../types';

interface UploadDocumentProps {
  onUploadSuccess?: () => void;
}

export function UploadDocument({ onUploadSuccess }: UploadDocumentProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      await apiClient<Document>('/api/v1/documents', {
        method: 'POST',
        body: formData,
      });
      onUploadSuccess?.();
    } catch (err: any) {
      console.error('Document upload failed:', err);
      setUploadError(err.message || 'Failed to upload document. Please check the file type.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        className="hidden"
        onChange={handleFileChange}
      />

      <button
        type="button"
        disabled={isUploading}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`w-full border ${
          isDragging
            ? 'border-penny-accent dark:border-penny-dark-accent bg-penny-accent/5'
            : 'border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface'
        } hover:bg-penny-border/20 dark:hover:bg-penny-dark-border/40 transition-colors py-16 flex flex-col items-center justify-center cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        <div className="flex items-center gap-3 text-penny-text dark:text-penny-dark-text">
          {isUploading ? (
            <Loader2 size={16} className="animate-spin text-penny-accent dark:text-penny-dark-accent" />
          ) : (
            <Plus size={16} className="group-hover:text-penny-accent dark:group-hover:text-penny-dark-accent transition-colors" />
          )}
          <span className="text-sm font-medium tracking-wide">
            {isUploading ? 'UPLOADING & PROCESSING...' : 'ADD DOCUMENT'}
          </span>
        </div>
        <span className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mt-3">
          {isUploading ? 'Extracting financial tables and generating vectors' : 'Drop PDF, DOCX, or TXT here'}
        </span>
      </button>

      {uploadError && (
        <div className="p-3 border border-penny-accent/40 bg-penny-accent/5 text-penny-accent dark:text-penny-dark-accent flex items-center gap-2.5 text-xs">
          <AlertCircle size={14} className="shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}
    </div>
  );
}