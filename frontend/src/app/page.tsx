"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Citation = {
  source_file: string;
  page_start: number;
  page_end: number;
  score: number;
  snippet: string;
};

type AssistantMessage = {
  role: "assistant";
  content: string;
  citations: Citation[];
  prompt?: string;
  level?: number | null;
};

type UserMessage = {
  role: "user";
  content: string;
};

type Message = AssistantMessage | UserMessage;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:9000";

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState<number | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<FileList | null>(null);
  const [serverStatus, setServerStatus] = useState<any>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Check server health on component mount
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
          const data = await res.json();
          setServerStatus(data);
        }
      } catch (e) {
        console.error('Health check failed:', e);
      }
    }
    checkHealth();
  }, []);

  const canSend = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  async function handleIngest() {
    if (!uploadedFiles || uploadedFiles.length === 0) {
      alert("Please select PDF files to upload first");
      return;
    }

    try {
      setIngesting(true);
      const formData = new FormData();
      
      for (let i = 0; i < uploadedFiles.length; i++) {
        formData.append('files', uploadedFiles[i]);
      }

      const res = await fetch(`${API_BASE}/ingest`, {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      alert(`Ingestion completed: ${data.message}`);
      setUploadedFiles(null);
    } catch (e: any) {
      console.error(e);
      alert(`Ingestion failed: ${e.message || "Unknown error"}`);
    } finally {
      setIngesting(false);
    }
  }

  async function handleSend() {
    if (!canSend) return;
    const question = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const queryParams = new URLSearchParams({
        question: question,
      });
      
      if (selectedLevel !== null) {
        queryParams.append('level', selectedLevel.toString());
      }

      const res = await fetch(`${API_BASE}/query?${queryParams}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      const assistant: AssistantMessage = {
        role: "assistant",
        content: data.answer || "",
        citations: (data.citations || []) as Citation[],
        prompt: data.prompt,
        level: selectedLevel,
      };
      setMessages((prev) => [...prev, assistant]);
    } catch (e: any) {
      console.error(e);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e.message || "failed"}`, citations: [], level: selectedLevel },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col">
      <header className="border-b border-neutral-800 px-4 py-3 flex items-center gap-3 sticky top-0 bg-neutral-950/80 backdrop-blur">
        <div className="font-semibold">Jharkhand Multi-Level RAG Chatbot</div>
        
        {/* Server Status Indicator */}
        {serverStatus && (
          <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${serverStatus.orchestrator === 'ok' ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="opacity-70">Orchestrator</span>
            {Object.entries(serverStatus.levels || {}).map(([level, status]: [string, any]) => (
              <div key={level} className="flex items-center gap-1">
                <div className={`w-2 h-2 rounded-full ${status.status === 'ok' ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="opacity-70">{level}</span>
              </div>
            ))}
          </div>
        )}
        
        <div className="ml-auto flex items-center gap-3">
          {/* File Upload */}
          <div className="flex items-center gap-2">
            <input
              type="file"
              id="pdf-upload"
              accept=".pdf"
              multiple
              onChange={(e) => setUploadedFiles(e.target.files)}
              className="hidden"
            />
            <label
              htmlFor="pdf-upload"
              className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 cursor-pointer text-sm"
            >
              {uploadedFiles ? `${uploadedFiles.length} files` : "Select PDFs"}
            </label>
          </div>
          
          {/* Ingest Button */}
          <button
            onClick={handleIngest}
            disabled={ingesting || !uploadedFiles}
            className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-sm"
            title="Upload and ingest PDF files"
          >
            {ingesting ? "Ingesting…" : "Ingest PDFs"}
          </button>
          
          {/* Level Selection */}
          <div className="flex items-center gap-2 text-sm">
            <label className="opacity-70">Level:</label>
            <select
              value={selectedLevel === null ? '' : selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value === '' ? null : parseInt(e.target.value))}
              className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm"
            >
              <option value="">Auto</option>
              <option value="0">Level 0 (General)</option>
              <option value="1">Level 1 (Summary)</option>
              <option value="2">Level 2 (Technical)</option>
            </select>
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto max-w-4xl px-4 py-6">
        <div className="space-y-6">
          {messages.map((m, idx) => (
            <MessageBubble key={idx} message={m} />
          ))}
          {loading && (
            <div className="opacity-70 text-sm">Assistant is typing…</div>
          )}
          <div ref={endRef} />
        </div>
      </main>

      <footer className="border-t border-neutral-800 p-4">
        <div className="container mx-auto max-w-4xl">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={selectedLevel === null ? "Ask a question about Jharkhand policies…" : `Ask a Level ${selectedLevel} question…`}
              className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-3 py-2 outline-none focus:border-neutral-600"
            />
            <button
              onClick={handleSend}
              disabled={!canSend}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-60"
            >
              Send
            </button>
          </div>
          <div className="mt-2 text-xs opacity-60">
            Backend: {API_BASE} | 
            {selectedLevel === null ? 'Auto-level selection' : `Level ${selectedLevel} queries`}
          </div>
        </div>
      </footer>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-blue-600 text-white rounded-lg px-4 py-2 whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="w-full">
        <div className="flex items-center gap-2 mb-2">
          <div className="text-xs opacity-60">Assistant</div>
          {message.level !== undefined && (
            <div className="text-xs px-2 py-1 rounded bg-blue-600/20 text-blue-400">
              Level {message.level}
            </div>
          )}
        </div>
        <div className="max-w-[90%] bg-neutral-900 rounded-lg px-4 py-3 whitespace-pre-wrap">
          {message.content || ""}
        </div>
        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 border border-neutral-800 rounded">
            <div className="px-3 py-2 text-sm font-medium bg-neutral-900 border-b border-neutral-800">
              Citations ({message.citations.length})
            </div>
            <div className="divide-y divide-neutral-800">
              {message.citations.map((c, i) => (
                <div key={i} className="px-3 py-2 text-sm">
                  <div className="font-medium">
                    {c.source_file} (pp. {c.page_start}-{c.page_end}) — score {c.score.toFixed(3)}
                  </div>
                  {c.snippet && (
                    <div className="mt-1 opacity-80 line-clamp-3">{c.snippet}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        {/* Prompt view */}
        {message.prompt && <PromptViewer prompt={message.prompt} />}
      </div>
    </div>
  );
}

function PromptViewer({ prompt }: { prompt: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs px-2 py-1 rounded border border-neutral-800 hover:border-neutral-700"
      >
        {open ? "Hide Prompt" : "Show Prompt"}
      </button>
      {open && (
        <pre className="mt-2 text-xs overflow-auto max-h-72 bg-neutral-900 p-3 rounded border border-neutral-800 whitespace-pre-wrap">
{prompt}
        </pre>
      )}
    </div>
  );
}
