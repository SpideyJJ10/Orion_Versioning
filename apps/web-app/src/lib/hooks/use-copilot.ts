"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";

export interface CopilotMessage {
  role: "user" | "assistant";
  content: string;
}

export function useCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      role: "assistant",
      content:
        "¡Hola! Soy tu copiloto Orion 🚀 Pregúntame sobre tus ventas, inventario o alertas de inteligencia artificial.",
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: CopilotMessage = { role: "user", content: text.trim() };
      const updated = [...messages, userMsg];
      setMessages(updated);
      setIsLoading(true);

      try {
        const history = messages
          .slice(-8)
          .map((m) => ({ role: m.role, content: m.content }));

        const data = await api.post<{ reply: string }>("/api/copilot/chat", {
          message: text.trim(),
          history,
        });

        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.reply },
        ]);
      } catch {
        toast.error("Copilot no está disponible en este momento.");
        // Remove the optimistic user message on error
        setMessages((prev) => prev.filter((m) => m !== userMsg));
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading]
  );

  return { isOpen, setIsOpen, messages, sendMessage, isLoading };
}
