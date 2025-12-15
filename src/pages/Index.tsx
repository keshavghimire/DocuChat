import { useState } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import { useChat } from '@/hooks/useChat';
import { DocumentSidebar } from '@/components/DocumentSidebar';
import { ChatInterface } from '@/components/ChatInterface';
import { FileUpload } from '@/components/FileUpload';
import { Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Index = () => {
  const { documents, loading, uploadDocument, deleteDocument } = useDocuments();
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const selectedDocument = documents.find(d => d.id === selectedDocId) || null;
  const { messages, isLoading: isChatLoading, sendMessage, clearMessages } = useChat(selectedDocId);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    const doc = await uploadDocument(file);
    setIsUploading(false);
    if (doc) {
      // Auto-select after upload
      setTimeout(() => {
        const readyDoc = documents.find(d => d.id === doc.id && d.status === 'READY');
        if (readyDoc) setSelectedDocId(readyDoc.id);
      }, 1000);
    }
  };

  const handleSelectDocument = (id: string) => {
    if (id !== selectedDocId) {
      setSelectedDocId(id);
      clearMessages();
    }
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 lg:hidden"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-40 w-72 bg-sidebar border-r border-sidebar-border
          transform transition-transform duration-300 ease-in-out
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex flex-col h-full">
          <div className="p-4 border-b border-sidebar-border flex items-center">
            <img 
              src="/logo.png?v=5" 
              alt="DocuChat" 
              className="h-10 w-auto max-w-full object-contain"
            />
          </div>
          <div className="flex-1 overflow-hidden">
            <DocumentSidebar
              documents={documents}
              selectedId={selectedDocId}
              onSelect={handleSelectDocument}
              onDelete={deleteDocument}
            />
          </div>
          <FileUpload onUpload={handleUpload} isUploading={isUploading} />
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Navbar */}
        <nav className="h-16 border-b border-border bg-card/50 backdrop-blur-sm flex items-center px-6 shrink-0">
          <div className="flex items-center gap-3">
            
            <h1 className="text-xl font-semibold">AI powered PDF chat</h1>
          </div>
        </nav>
        <div className="flex-1 min-h-0">
          <ChatInterface
            messages={messages}
            isLoading={isChatLoading}
            onSendMessage={sendMessage}
            selectedDocument={selectedDocument}
          />
        </div>
      </main>
    </div>
  );
};

export default Index;
