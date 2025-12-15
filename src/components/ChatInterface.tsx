import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ChatMessage, Document } from '@/types/document';
import { cn } from '@/lib/utils';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  selectedDocument: Document | null;
}

export function ChatInterface({ messages, isLoading, onSendMessage, selectedDocument }: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !selectedDocument) return;
    onSendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!selectedDocument) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-6">
          <FileText className="h-10 w-10 text-primary" />
        </div>
        <h2 className="text-2xl font-semibold mb-2">DocuChat</h2>
        <p className="text-muted-foreground max-w-md">
          Upload a PDF document and select it to start asking questions about its content.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Document header */}
      <div className="p-4 border-b border-border bg-card/50">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-primary" />
          <div>
            <h3 className="font-medium">{selectedDocument.file_name}</h3>
            <p className="text-xs text-muted-foreground">{selectedDocument.pages} pages</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-muted-foreground mb-4">Ask a question about this document</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {['What is this document about?', 'Summarize the key points', 'What are the main findings?'].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="px-3 py-2 text-sm bg-secondary hover:bg-secondary/80 rounded-lg transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "message-enter max-w-3xl",
                message.role === 'user' ? 'ml-auto' : 'mr-auto'
              )}
            >
              <div
                className={cn(
                  "p-4 rounded-2xl",
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-br-md'
                    : 'bg-card border border-border rounded-bl-md'
                )}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="text-xs text-muted-foreground">Sources:</span>
                  {[...new Set(message.sources.map(s => s.pageNumber))].map((page) => (
                    <span key={page} className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded">
                      Page {page}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border bg-card/30">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about this document..."
            rows={1}
            className="flex-1 resize-none bg-secondary border-0 rounded-xl px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <Button type="submit" size="icon" className="h-12 w-12 rounded-xl" disabled={isLoading || !input.trim()}>
            <Send className="h-5 w-5" />
          </Button>
        </div>
      </form>
    </div>
  );
}
