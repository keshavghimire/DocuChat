import { useState, useEffect } from 'react';
import { Document } from '@/types/document';
import { useToast } from '@/hooks/use-toast';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? '/api' : 'http://localhost:8080/api');

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      const data = await response.json();
      
      // Transform backend response to frontend format
      const transformedDocs: Document[] = data.map((doc: any) => ({
        id: doc.documentId,
        file_name: doc.fileName,
        file_size: doc.fileSize,
        pages: doc.pages || 0,
        status: doc.status as Document['status'],
        error_message: doc.errorMessage || null,
        created_at: doc.createdAt,
        updated_at: doc.updatedAt,
      }));
      
      setDocuments(transformedDocs);
    } catch (error) {
      console.error('Error fetching documents:', error);
      toast({
        title: 'Error',
        description: 'Failed to fetch documents',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const uploadDocument = async (file: File): Promise<Document | null> => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorMessage = 'Failed to upload document';
        try {
          const errorData = await response.json();
          // Handle both ErrorResponse format and other error formats
          if (errorData.message) {
            errorMessage = errorData.message;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          } else if (typeof errorData === 'string') {
            errorMessage = errorData;
          } else {
            errorMessage = errorData.message || errorData.error || `${response.status} ${response.statusText}`;
          }
        } catch {
          // If response is not JSON, use status text
          errorMessage = `${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const docData = await response.json();
      
      // Transform backend response to frontend format
      const document: Document = {
        id: docData.documentId,
        file_name: docData.fileName,
        file_size: docData.fileSize,
        pages: docData.pages || 0,
        status: docData.status as Document['status'],
        error_message: docData.errorMessage || null,
        created_at: docData.createdAt,
        updated_at: docData.updatedAt,
      };

      // Poll for status updates
      pollDocumentStatus(document.id);
      
      fetchDocuments();
      return document;
    } catch (error) {
      console.error('Error uploading document:', error);
      toast({
        title: 'Upload Failed',
        description: error instanceof Error ? error.message : 'Failed to upload document',
        variant: 'destructive',
      });
      return null;
    }
  };

  const pollDocumentStatus = async (documentId: string) => {
    const maxAttempts = 60; // 5 minutes max
    let attempts = 0;
    
    const poll = async () => {
      if (attempts >= maxAttempts) return;
      
      try {
        const response = await fetch(`${API_BASE_URL}/documents/${documentId}`);
        if (response.ok) {
          const docData = await response.json();
          const status = docData.status;
          
          setDocuments(prev => prev.map(doc => 
            doc.id === documentId 
              ? {
                  ...doc,
                  status: status as Document['status'],
                  pages: docData.pages || doc.pages,
                  error_message: docData.errorMessage || null,
                }
              : doc
          ));
          
          if (status === 'READY' || status === 'ERROR') {
            return; // Stop polling
          }
        }
      } catch (error) {
        console.error('Error polling document status:', error);
      }
      
      attempts++;
      setTimeout(poll, 5000); // Poll every 5 seconds
    };
    
    poll();
  };

  const deleteDocument = async (documentId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete document');
      }

      setDocuments(docs => docs.filter(d => d.id !== documentId));
      
      toast({
        title: 'Deleted',
        description: 'Document deleted successfully',
      });
    } catch (error) {
      console.error('Error deleting document:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete document',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    fetchDocuments();
    
    // Poll for document status updates every 10 seconds
    const interval = setInterval(() => {
      const processingDocs = documents.filter(d => d.status === 'PROCESSING' || d.status === 'UPLOADING');
      processingDocs.forEach(doc => {
        fetch(`${API_BASE_URL}/documents/${doc.id}`)
          .then(res => res.json())
          .then(docData => {
            setDocuments(prev => prev.map(d => 
              d.id === doc.id 
                ? {
                    ...d,
                    status: docData.status as Document['status'],
                    pages: docData.pages || d.pages,
                    error_message: docData.errorMessage || null,
                  }
                : d
            ));
          })
          .catch(err => console.error('Error polling:', err));
      });
    }, 10000);
    
    return () => clearInterval(interval);
  }, []);

  return {
    documents,
    loading,
    uploadDocument,
    deleteDocument,
    refetch: fetchDocuments,
  };
}
