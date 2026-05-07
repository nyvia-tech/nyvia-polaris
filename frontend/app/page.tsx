"use client";

import { useState } from "react";
import Chat from "./components/Chat";
import Eval from "./components/Eval";

type Tab = "chat" | "eval";

export default function Home() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div className="flex h-screen bg-nyvia-dark">
      {/* Sidebar */}
      <div className="w-36 border-r border-nyvia-border flex flex-col pt-4 gap-1 px-2 shrink-0">
        {(["chat", "eval"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all text-left ${
              tab === t
                ? "bg-nyvia-surface border border-nyvia-border text-white"
                : "text-nyvia-muted hover:text-white"
            }`}
          >
            {t === "chat" ? "Chat" : "Evaluación"}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {tab === "chat" ? <Chat /> : <Eval />}
      </div>
    </div>
  );
}
