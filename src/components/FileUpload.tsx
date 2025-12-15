import { useState, useCallback } from 'react';
import { Upload, FileText, X, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

export function FileUpload({ onUpload, isUploading }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const validateFile = (file: File): boolean => {
    setError(null);
    
    if (!file) {
      setError('No file selected');
      return false;
    }
    
    if (file.type !== 'application/pdf') {
      setError('Only PDF files are supported');
      toast({
        title: 'Invalid File Type',
        description: 'Please select a PDF file',
        variant: 'destructive',
      });
      return false;
    }
    
    if (file.size === 0) {
      setError('File is empty');
      return false;
    }
    
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      setError(`File size exceeds 50MB limit (${(file.size / 1024 / 1024).toFixed(2)}MB)`);
      toast({
        title: 'File Too Large',
        description: `File size (${(file.size / 1024 / 1024).toFixed(2)}MB) exceeds the 50MB limit`,
        variant: 'destructive',
      });
      return false;
    }
    
    return true;
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragging(true);
    } else if (e.type === 'dragleave') {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
    if (pdfFile && validateFile(pdfFile)) {
      setSelectedFile(pdfFile);
    } else if (files.length > 0 && !pdfFile) {
      setError('Only PDF files are supported');
      toast({
        title: 'Invalid File Type',
        description: 'Please drop a PDF file',
        variant: 'destructive',
      });
    }
  }, [toast]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (validateFile(file)) {
        setSelectedFile(file);
      } else {
        // Reset input
        e.target.value = '';
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    try {
      await onUpload(selectedFile);
      setSelectedFile(null);
      setError(null);
    } catch (err) {
      // Error is handled by the parent component via toast
      console.error('Upload error:', err);
    }
  };

  return (
    <div className="p-4 border-t border-border">
      {error && (
        <div className="mb-3 p-2 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
      {selectedFile ? (
        <div className="flex items-center gap-3 p-3 bg-secondary rounded-lg">
          <FileText className="h-8 w-8 text-primary" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{selectedFile.name}</p>
            <p className="text-xs text-muted-foreground">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          {isUploading ? (
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          ) : (
            <>
              <Button size="sm" onClick={handleUpload}>Upload</Button>
              <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => {
                setSelectedFile(null);
                setError(null);
              }}>
                <X className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      ) : (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={cn(
            "drop-zone p-6 text-center cursor-pointer",
            isDragging && "drop-zone-active"
          )}
        >
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
            id="pdf-upload"
          />
          <label htmlFor="pdf-upload" className="cursor-pointer">
            <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Drop a PDF here or <span className="text-primary">browse</span>
            </p>
          </label>
        </div>
      )}
    </div>
  );
}
