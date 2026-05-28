"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

interface Source {
  source: string;
  score: number;
  text: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  traceId?: string;
  feedback?: 1 | 0 | null;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await fetch("/api/backend/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!res.ok) throw new Error(`Error ${res.status}`);

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          traceId: data.trace_id ?? null,
          feedback: null,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Hubo un error al procesar tu pregunta. Por favor intenta de nuevo.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function sendFeedback(msgIndex: number, value: 1 | 0) {
    const msg = messages[msgIndex];
    if (!msg.traceId || msg.feedback !== null) return;

    setMessages((prev) =>
      prev.map((m, i) => (i === msgIndex ? { ...m, feedback: value } : m))
    );

    try {
      await fetch("/api/backend/chat/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trace_id: msg.traceId, value }),
      });
    } catch {
      // feedback is best-effort, don't revert UI on failure
    }
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto px-4">
      {/* Header */}
      <div className="py-5 border-b border-nyvia-border">
        <h1 className="text-2xl font-bold text-white">
          Nyvia <span className="text-nyvia-accent">Polaris</span>
        </h1>
        <p className="text-nyvia-muted text-sm mt-1">Base de conocimiento interna</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-6 space-y-6">
        {messages.length === 0 && (
          <div className="text-center text-nyvia-muted mt-20">
            <p className="text-lg">¿Qué quieres saber sobre Nyvia?</p>
            <p className="text-sm mt-2">Pregunta sobre metodologías, clientes, servicios o procesos internos.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-nyvia-accent text-white"
                  : "bg-nyvia-surface border border-nyvia-border text-nyvia-text"
              }`}
            >
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>

              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-nyvia-border">
                  <p className="text-xs text-nyvia-muted mb-2">Fuentes:</p>
                  <div className="space-y-1">
                    {msg.sources.map((s, j) => (
                      <details key={j} className="text-xs">
                        <summary className="cursor-pointer text-nyvia-accent hover:underline">
                          {s.source} (relevancia: {(s.score * 100).toFixed(0)}%)
                        </summary>
                        <p className="mt-1 text-nyvia-muted pl-2 border-l border-nyvia-border">
                          {s.text}
                        </p>
                      </details>
                    ))}
                  </div>
                </div>
              )}

              {msg.role === "assistant" && msg.traceId && (
                <div className="mt-3 pt-3 border-t border-nyvia-border flex items-center gap-3">
                  {msg.feedback === null ? (
                    <>
                      <span className="text-xs text-nyvia-muted">¿Fue útil?</span>
                      <button
                        onClick={() => sendFeedback(i, 1)}
                        className="text-xs text-nyvia-muted hover:text-nyvia-accent transition-colors"
                        title="Útil"
                      >
                        👍 Útil
                      </button>
                      <button
                        onClick={() => sendFeedback(i, 0)}
                        className="text-xs text-nyvia-muted hover:text-red-400 transition-colors"
                        title="No útil"
                      >
                        👎 No útil
                      </button>
                    </>
                  ) : (
                    <span className="text-xs text-nyvia-muted">
                      {msg.feedback === 1 ? "👍 Gracias por tu feedback" : "👎 Gracias, lo tendremos en cuenta"}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-nyvia-surface border border-nyvia-border rounded-2xl px-4 py-3">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-nyvia-accent rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-2 h-2 bg-nyvia-accent rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-2 h-2 bg-nyvia-accent rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="py-4 border-t border-nyvia-border">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Pregunta al Nyvia Brain..."
            disabled={loading}
            className="flex-1 bg-nyvia-surface border border-nyvia-border rounded-xl px-4 py-3 text-nyvia-text placeholder-nyvia-muted focus:outline-none focus:border-nyvia-accent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-nyvia-accent hover:bg-opacity-80 disabled:opacity-40 text-white px-5 py-3 rounded-xl font-medium transition-all"
          >
            Enviar
          </button>
        </div>
      </form>
    </div>
  );
}
