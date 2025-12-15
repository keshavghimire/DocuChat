export interface Document {
  id: string;
  file_name: string;
  file_size: number | null;
  pages: number;
  status: 'UPLOADING' | 'PROCESSING' | 'READY' | 'ERROR';
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  page_number: number;
  chunk_index: number;
  chunk_text: string;
  embedding: number[] | null;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}

export interface Source {
  pageNumber: number;
  snippet: string;
  similarity?: number;
}

export interface ChatQueryResponse {
  answer: string;
  sources: Source[];
}
