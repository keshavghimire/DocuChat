import { FileText, Trash2, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { Document } from '@/types/document';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DocumentSidebarProps {
  documents: Document[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function DocumentSidebar({ documents, selectedId, onSelect, onDelete }: DocumentSidebarProps) {
  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'PROCESSING':
      case 'UPLOADING':
        return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
      case 'READY':
        return <CheckCircle className="h-4 w-4 text-success" />;
      case 'ERROR':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground">Documents</h2>
        <p className="text-sm text-muted-foreground mt-1">{documents.length} uploaded</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8 px-4">
            Upload a PDF to get started
          </p>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className={cn(
                "group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all",
                selectedId === doc.id
                  ? "bg-primary/10 border border-primary/30"
                  : "hover:bg-secondary border border-transparent"
              )}
              onClick={() => doc.status === 'READY' && onSelect(doc.id)}
            >
              <FileText className="h-5 w-5 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.file_name}</p>
                <p className="text-xs text-muted-foreground">
                  {doc.pages > 0 ? `${doc.pages} pages` : doc.status}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {getStatusIcon(doc.status)}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(doc.id);
                  }}
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
