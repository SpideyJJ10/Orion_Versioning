"use client";

import { useRef, useEffect, useState } from "react";
import { Brain, Send, X, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { useCopilot, CopilotMessage } from "@/lib/hooks/use-copilot";
import { cn } from "@/lib/utils";

function renderMarkdown(text: string) {
  // Simple regex for bold -> <strong> conversion
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

export function CopilotWidget() {
  const { isOpen, setIsOpen, messages, sendMessage, isLoading } = useCopilot();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button 
          className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-xl gradient-orion hover:scale-105 transition-transform p-0"
          title="Abrir Copiloto Orion"
        >
          <Sparkles className="h-6 w-6 text-white" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-md flex flex-col h-full border-l p-0 sm:p-0">
        <SheetHeader className="p-4 border-b bg-muted/30">
          <SheetTitle className="flex items-center gap-2 text-lg">
            <Brain className="h-5 w-5 text-primary" />
            Orion Intelligence Copilot
          </SheetTitle>
        </SheetHeader>
        
        <div className="flex-1 p-4 overflow-y-auto" ref={scrollRef}>
          <div className="flex flex-col gap-4">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={cn(
                  "max-w-[85%] rounded-2xl p-3 text-sm",
                  msg.role === "user" 
                    ? "bg-primary text-primary-foreground self-end rounded-tr-sm" 
                    : "bg-muted text-foreground self-start rounded-tl-sm"
                )}
              >
                {renderMarkdown(msg.content)}
              </div>
            ))}
            {isLoading && (
              <div className="bg-muted text-foreground self-start rounded-2xl rounded-tl-sm p-3 max-w-[85%] flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Pensando...</span>
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-4 border-t bg-background flex gap-2">
          <Input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Escribe tu mensaje..."
            className="flex-1"
            disabled={isLoading}
          />
          <Button type="submit" disabled={!input.trim() || isLoading} className="gradient-orion">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </SheetContent>
    </Sheet>
  );
}
