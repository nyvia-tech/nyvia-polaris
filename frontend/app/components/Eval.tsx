"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

interface JudgeResult {
  score: number;
  verdict: string;
  unsupported_claims?: string;
  missing_aspects?: string;
}

interface EvalResult {
  question: string;
  rag_answer: string;
  sources: string[];
  groundedness: JudgeResult;
  relevance: JudgeResult;
}

function ScoreBar({ label, result, detailKey }: {
  label: string;
  result: JudgeResult;
  detailKey: "unsupported_claims" | "missing_aspects";
}) {
  const s = result.score;
  const color = s >= 80 ? "bg-green-500" : s >= 60 ? "bg-yellow-500" : "bg-red-500";
  const textColor = s >= 80 ? "text-green-400" : s >= 60 ? "text-yellow-400" : "text-red-400";
  const detail = result[detailKey];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-white">{label}</span>
        <span className="text-2xl font-bold text-white">
          {s}<span className="text-base text-nyvia-muted">/100</span>
        </span>
      </div>
      <div className="w-full bg-nyvia-surface rounded-full h-3 border border-nyvia-border">
        <div className={`h-3 rounded-full transition-all duration-700 ${color}`} style={{ width: `${s}%` }} />
      </div>
      <p className={`text-xs font-medium ${textColor}`}>{result.verdict}</p>
      {detail && detail !== "Ninguna" && detail !== "Ninguno" && detail !== "N/A" && (
        <p className="text-xs text-nyvia-muted mt-1">
          <span className="text-yellow-400 font-semibold">⚠ </span>{detail}
        </p>
      )}
    </div>
  );
}

export default function Eval() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [error, setError] = useState("");

  async function runEval(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;

    setLoading(true);
    setResult(null);
    setError("");

    try {
      const res = await fetch("/api/backend/eval/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      setResult(await res.json());
    } catch {
      setError("Error al conectar con el backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white">Evaluación LLM-as-Judge</h2>
        <p className="text-nyvia-muted text-sm mt-1">
          Evalúa la calidad de la respuesta RAG: groundedness (¿se sostiene en el contexto?) y relevance (¿responde la pregunta?).
        </p>
      </div>

      {/* Input */}
      <form onSubmit={runEval} className="flex gap-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Escribe una pregunta para evaluar..."
          disabled={loading}
          className="flex-1 bg-nyvia-surface border border-nyvia-border rounded-xl px-4 py-3 text-nyvia-text placeholder-nyvia-muted focus:outline-none focus:border-nyvia-accent disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="bg-nyvia-accent hover:bg-opacity-80 disabled:opacity-40 text-white px-5 py-3 rounded-xl font-medium transition-all whitespace-nowrap"
        >
          {loading ? "Evaluando..." : "Evaluar"}
        </button>
      </form>

      {loading && (
        <div className="bg-nyvia-surface border border-nyvia-border rounded-2xl p-6 text-center space-y-3">
          <div className="flex justify-center space-x-1">
            <div className="w-2 h-2 bg-nyvia-accent rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <div className="w-2 h-2 bg-nyvia-accent rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <div className="w-2 h-2 bg-nyvia-accent rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
          <p className="text-nyvia-muted text-sm">Generando respuesta y evaluando... esto tarda ~10 segundos.</p>
        </div>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {result && (
        <div className="space-y-6">
          {/* Scores */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-nyvia-surface border border-nyvia-border rounded-2xl p-5">
              <ScoreBar
                label="Groundedness"
                result={result.groundedness}
                detailKey="unsupported_claims"
              />
            </div>
            <div className="bg-nyvia-surface border border-nyvia-border rounded-2xl p-5">
              <ScoreBar
                label="Relevance"
                result={result.relevance}
                detailKey="missing_aspects"
              />
            </div>
          </div>

          {/* RAG Answer */}
          <div className="bg-nyvia-surface border border-nyvia-accent/40 rounded-2xl p-5 space-y-3">
            <p className="text-xs font-semibold text-nyvia-accent uppercase tracking-wide">Respuesta RAG</p>
            <div className="prose prose-invert prose-sm max-w-none text-nyvia-text">
              <ReactMarkdown>{result.rag_answer}</ReactMarkdown>
            </div>
          </div>

          {/* Sources */}
          {result.sources.length > 0 && (
            <div className="bg-nyvia-surface border border-nyvia-border rounded-2xl p-5 space-y-2">
              <p className="text-xs font-semibold text-nyvia-muted uppercase tracking-wide">Fuentes consultadas</p>
              <div className="flex flex-wrap gap-2">
                {result.sources.map((s) => (
                  <span key={s} className="text-xs bg-nyvia-border text-nyvia-text px-3 py-1 rounded-full">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
