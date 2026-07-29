"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Send, Bot, Sparkles, Building2, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OrionLogo } from "@/components/brand/orion-logo";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { toast } from "sonner";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function OIAPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      role: "assistant",
      content: "¡Hola! Soy Orion IA. Estoy aquí para ayudarte a crear y configurar el software perfecto para tu negocio. ¿De qué trata tu negocio?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const setSession = useAuthStore((s) => s.setSession);

  // Auto-scroll al último mensaje
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSend(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    
    // Add user message
    const newMessages: Message[] = [
      ...messages,
      { id: Date.now().toString(), role: "user", content: userMessage },
    ];
    setMessages(newMessages);
    setLoading(true);

    try {
      const response = await api.post<{
        reply: string;
        extracted: any;
        ready_to_provision: boolean;
        confidence: number;
        session_id: string;
      }>("/api/oai/chat", {
        session_id: sessionId,
        history: newMessages.map(m => ({ role: m.role, content: m.content })),
        message: userMessage
      });

      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: "assistant", content: response.reply },
      ]);

      if (response.ready_to_provision) {
        // Ejecutar provision!
        handleProvision(response.extracted);
      }
    } catch (err) {
      toast.error("Ocurrió un error al contactar a Orion IA.");
    } finally {
      setLoading(false);
    }
  }

  async function handleProvision(extracted: any) {
    try {
      toast.loading("Creando tu negocio...", { id: "provision" });
      const provisionReq = {
        email: extracted.email,
        password: extracted.password || "Orion123!", // Dummy password if not asked
        nombre_negocio: extracted.nombre_negocio,
        tipo_negocio: extracted.tipo_negocio,
        num_mesas: extracted.num_mesas || 0,
        maneja_domicilios: extracted.maneja_domicilios || false
      };

      const result = await api.post<any>("/api/oai/provision", provisionReq);
      
      toast.success("¡Negocio creado con éxito!", { id: "provision" });
      setSession(result.access_token, result.refresh_token, result.usuario);
      router.push("/");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Fallo al crear el negocio", { id: "provision" });
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/80 px-6 py-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <OrionLogo variant="mark" size="md" />
          <div>
            <h1 className="text-xl font-bold tracking-tight">Orion IA</h1>
            <p className="text-sm text-muted-foreground">Tu creador de SaaS personal</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1 text-xs font-medium text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          Powered by LLM
        </div>
      </header>

      {/* Chat Area */}
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col p-4 md:p-6 overflow-hidden">
        <div className="flex-1 pr-4 overflow-y-auto" ref={scrollRef}>
          <div className="flex flex-col gap-6 pb-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border shadow-sm ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-card text-foreground"
                  }`}
                >
                  {msg.role === "user" ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5 text-primary" />}
                </div>
                <div
                  className={`flex max-w-[80%] flex-col gap-2 rounded-2xl px-5 py-3 text-sm shadow-sm ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "border bg-card text-foreground"
                  }`}
                >
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border bg-card text-foreground shadow-sm">
                  <Bot className="h-5 w-5 text-primary animate-pulse" />
                </div>
                <div className="flex items-center rounded-2xl border bg-card px-5 py-4 text-sm shadow-sm">
                  <div className="flex gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-primary/40 animate-bounce" />
                    <span className="h-2 w-2 rounded-full bg-primary/60 animate-bounce [animation-delay:0.2s]" />
                    <span className="h-2 w-2 rounded-full bg-primary/80 animate-bounce [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="pt-4">
          <form
            onSubmit={handleSend}
            className="relative flex items-center overflow-hidden rounded-full border bg-card p-1 focus-within:ring-2 focus-within:ring-primary shadow-sm"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu mensaje..."
              className="border-0 bg-transparent px-4 focus-visible:ring-0 focus-visible:ring-offset-0 text-base"
              disabled={loading}
            />
            <Button
              type="submit"
              size="icon"
              disabled={!input.trim() || loading}
              className="h-10 w-10 shrink-0 rounded-full"
            >
              <Send className="h-4 w-4" />
              <span className="sr-only">Enviar</span>
            </Button>
          </form>
          <div className="mt-3 text-center text-xs text-muted-foreground">
            Orion IA puede cometer errores. Considera verificar la información importante.
          </div>
        </div>
      </main>
    </div>
  );
}
