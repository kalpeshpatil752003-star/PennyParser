export interface User {
  id?: number;
  email: string;
  fullName: string;
}

export interface AuthResponse {
  accessToken: string;
  email: string;
  fullName: string;
}

export type DocumentStatus = 'UPLOADED' | 'EXTRACTING' | 'CHUNKING' | 'EMBEDDING' | 'READY' | 'FAILED';

export interface Document {
  id: number;
  fileName: string;
  fileType: string;
  documentType?: string;
  status: DocumentStatus;
  uploadedAt: string;
}

export interface Citation {
  documentId: number;
  page: number;
}

export interface ChatMessage {
  id: number;
  role: 'USER' | 'ASSISTANT';
  content: string;
  citations: Citation[];
  createdAt: string;
}

export interface Chat {
  id: number;
  title: string;
  createdAt: string;
  documents?: Document[];
}

export interface FinancialMetric {
  id: number;
  metricName: string;
  metricValue: number;
  unit: string;
  sourcePage?: number;
}

export interface FinancialStatement {
  id: number;
  documentId: number;
  statementType: string;
  fiscalYear?: number;
  period?: string;
  metrics: FinancialMetric[];
}