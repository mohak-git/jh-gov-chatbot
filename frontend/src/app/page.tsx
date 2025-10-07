"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { FaFilePdf } from "react-icons/fa";
import {
    FiAlertCircle,
    FiBook,
    FiCheckCircle,
    FiChevronDown,
    FiChevronUp,
    FiClock,
    FiCode,
    FiFile,
    FiFileText,
    FiInfo,
    FiMessageSquare,
    FiSend,
    FiX,
} from "react-icons/fi";
import { IoCheckmarkCircle, IoDocumentText } from "react-icons/io5";

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
    level?: number;
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
    const [selectedLevel, setSelectedLevel] = useState<number>(3);
    const [uploadedFiles, setUploadedFiles] = useState<FileList | null>(null);
    const [serverStatus, setServerStatus] = useState<any>(null);
    const [isLevelDropdownOpen, setIsLevelDropdownOpen] = useState(false);
    const [isServerStatusOpen, setIsServerStatusOpen] = useState(false);
    const endRef = useRef<HTMLDivElement | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(
                textareaRef.current.scrollHeight,
                120
            )}px`;
        }
    }, [input]);

    useEffect(() => {
        async function checkHealth() {
            try {
                const res = await fetch(`${API_BASE}/health`);
                if (res.ok) {
                    const data = await res.json();
                    // Ensure we have a status field for UI to work with
                    setServerStatus({
                        status: "healthy",
                        message: "Server is operational",
                        ...data, // spread any additional data from the response
                    });
                } else {
                    setServerStatus({
                        status: "error",
                        message: `Server returned ${res.status}`,
                        details: await res.text(),
                    });
                }
            } catch (e) {
                console.error("Health check failed:", e);
                setServerStatus({
                    status: "error",
                    message: "Connection failed",
                    details: e instanceof Error ? e.message : "Unknown error",
                });
            }
        }
        checkHealth();

        // Check server status every 30 seconds
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    const canSend = useMemo(
        () => input.trim().length > 0 && !loading,
        [input, loading]
    );

    async function handleIngest() {
        if (!uploadedFiles || uploadedFiles.length === 0) return;

        try {
            setIngesting(true);
            const formData = new FormData();

            for (let i = 0; i < uploadedFiles.length; i++) {
                formData.append("files", uploadedFiles[i]);
            }

            const res = await fetch(`${API_BASE}/ingest`, {
                method: "POST",
                body: formData,
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            await res.json();
            setUploadedFiles(null);
            if (fileInputRef.current) fileInputRef.current.value = "";
        } catch (e) {
            console.error(e);
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
                question,
                ...(selectedLevel !== 3 && { level: selectedLevel.toString() }),
            });

            const res = await fetch(`${API_BASE}/query?${queryParams}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const data = await res.json();
            const raw = data.answer;

            const assistant: AssistantMessage = {
                role: "assistant",
                content: raw.answer || "",
                citations: (raw.citations || []) as Citation[],
                prompt: raw.prompt,
                level: selectedLevel,
            };

            setMessages((prev) => [...prev, assistant]);
        } catch (e: any) {
            console.error(e);
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: `Error: ${e.message || "Failed to get response"}`,
                    citations: [],
                    level: selectedLevel,
                },
            ]);
        } finally {
            setLoading(false);
        }
    }

    function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }

    const LevelConfig = {
        0: {
            name: "General",
            icon: FiMessageSquare,
            color: "from-green-500 to-emerald-500",
            description: "Simple explanations for everyone",
        },
        1: {
            name: "Summary",
            icon: IoDocumentText,
            color: "from-blue-500 to-cyan-500",
            description: "Concise overviews with key points",
        },
        2: {
            name: "Technical",
            icon: FiCode,
            color: "from-purple-500 to-indigo-500",
            description: "Detailed analysis with technical depth",
        },
        3: {
            name: "Auto",
            icon: FiInfo,
            color: "from-orange-500 to-yellow-500",
            description:
                "Automatically detects the best level for the question",
        },
    };

    const getServerStatusColor = () => {
        if (!serverStatus) return "bg-gray-500";
        if (serverStatus.status === "healthy") return "bg-emerald-500";
        if (serverStatus.status === "warning") return "bg-amber-500";
        return "bg-red-500";
    };

    const getServerStatusIcon = () => {
        if (!serverStatus) return FiClock;
        if (serverStatus.status === "healthy") return FiCheckCircle;
        if (serverStatus.status === "warning") return FiAlertCircle;
        return FiAlertCircle;
    };

    const ServerStatusIcon = getServerStatusIcon();

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white flex flex-col">
            {/* Header */}
            <header className="border-b border-gray-700/50 bg-gray-900/80 backdrop-blur-xl px-6 py-4 sticky top-0 z-50">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
                                <FiBook className="w-6 h-6 text-white" />
                            </div>
                            <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-400 rounded-full border-2 border-gray-900 flex items-center justify-center">
                                <FiCheckCircle className="w-3 h-3 text-gray-900" />
                            </div>
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">
                                Jharkhand RAG
                            </h1>
                            <p className="text-sm text-gray-400">
                                Multi-level Policy Intelligence
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Server Status */}
                        <div className="relative">
                            <button
                                onClick={() =>
                                    setIsServerStatusOpen(!isServerStatusOpen)
                                }
                                className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all duration-200 ${
                                    serverStatus?.status === "healthy"
                                        ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                                        : serverStatus?.status === "warning"
                                        ? "border-amber-500/50 bg-amber-500/10 text-amber-300"
                                        : "border-red-500/50 bg-red-500/10 text-red-300"
                                }`}
                            >
                                <div
                                    className={`w-3 h-3 rounded-full ${getServerStatusColor()}`}
                                ></div>
                                <span className="text-sm font-medium">
                                    Server
                                </span>
                                <FiChevronDown
                                    className={`w-4 h-4 transition-transform duration-200 ${
                                        isServerStatusOpen ? "rotate-180" : ""
                                    }`}
                                />
                            </button>

                            <AnimatePresence>
                                {isServerStatusOpen && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -10 }}
                                        className="absolute top-full right-0 mt-2 w-64 bg-gray-800 border border-gray-600/50 rounded-xl shadow-2xl backdrop-blur-xl z-50 p-4"
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <ServerStatusIcon
                                                className={`w-5 h-5 ${
                                                    serverStatus?.status ===
                                                    "healthy"
                                                        ? "text-emerald-400"
                                                        : serverStatus?.status ===
                                                          "warning"
                                                        ? "text-amber-400"
                                                        : "text-red-400"
                                                }`}
                                            />
                                            <h3 className="font-semibold">
                                                {serverStatus?.status ===
                                                "healthy"
                                                    ? "System Operational"
                                                    : serverStatus?.status ===
                                                      "warning"
                                                    ? "System Warning"
                                                    : "System Down"}
                                            </h3>
                                        </div>
                                        <p className="text-sm text-gray-300 mb-3">
                                            {serverStatus?.message ||
                                                "Checking server status..."}
                                        </p>
                                        {serverStatus?.details && (
                                            <div className="text-xs text-gray-400 space-y-1">
                                                <div className="flex justify-between">
                                                    <span>Documents:</span>
                                                    <span>
                                                        {
                                                            serverStatus.details
                                                                .document_count
                                                        }
                                                    </span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span>Index Size:</span>
                                                    <span>
                                                        {
                                                            serverStatus.details
                                                                .index_size
                                                        }
                                                    </span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span>Uptime:</span>
                                                    <span>
                                                        {
                                                            serverStatus.details
                                                                .uptime
                                                        }
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* File Upload */}
                        <div className="relative">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf"
                                multiple
                                onChange={(e) =>
                                    setUploadedFiles(e.target.files)
                                }
                                className="hidden"
                            />
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all duration-200 ${
                                    uploadedFiles
                                        ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
                                        : "border-gray-600/50 bg-gray-800/50 text-gray-300 hover:border-gray-500"
                                }`}
                            >
                                <FiFile className="w-4 h-4" />
                                <span className="text-sm">
                                    {uploadedFiles
                                        ? `${uploadedFiles.length} file${
                                              uploadedFiles.length > 1
                                                  ? "s"
                                                  : ""
                                          }`
                                        : "Upload PDFs"}
                                </span>
                                {uploadedFiles && (
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setUploadedFiles(null);
                                            if (fileInputRef.current)
                                                fileInputRef.current.value = "";
                                        }}
                                        className="ml-1 -mr-1 w-5 h-5 rounded-full bg-gray-700 flex items-center justify-center hover:bg-gray-600"
                                    >
                                        <FiX className="w-3 h-3" />
                                    </button>
                                )}
                            </button>
                        </div>

                        {/* Ingest Button */}
                        <button
                            onClick={handleIngest}
                            disabled={ingesting || !uploadedFiles}
                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white text-sm font-medium hover:from-emerald-600 hover:to-teal-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-emerald-500/20"
                        >
                            {ingesting ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <IoCheckmarkCircle className="w-4 h-4" />
                            )}
                            {ingesting ? "Processing..." : "Process"}
                        </button>

                        {/* Level Selector */}
                        <div className="relative">
                            <button
                                onClick={() =>
                                    setIsLevelDropdownOpen(!isLevelDropdownOpen)
                                }
                                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-800/50 border border-gray-600/50 hover:border-gray-500 transition-all duration-200"
                            >
                                <div
                                    className={`w-3 h-3 rounded-full bg-gradient-to-r ${
                                        LevelConfig[
                                            selectedLevel as keyof typeof LevelConfig
                                        ].color
                                    }`}
                                />
                                <span className="text-sm font-medium">
                                    {
                                        LevelConfig[
                                            selectedLevel as keyof typeof LevelConfig
                                        ].name
                                    }
                                </span>
                                <FiChevronDown
                                    className={`w-4 h-4 transition-transform duration-200 ${
                                        isLevelDropdownOpen ? "rotate-180" : ""
                                    }`}
                                />
                            </button>

                            <AnimatePresence>
                                {isLevelDropdownOpen && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -10 }}
                                        className="absolute top-full right-0 mt-2 w-64 bg-gray-800 border border-gray-600/50 rounded-xl shadow-2xl backdrop-blur-xl z-50"
                                    >
                                        {[3, 2, 1, 0].map((level) => {
                                            const Config =
                                                LevelConfig[
                                                    level as keyof typeof LevelConfig
                                                ];
                                            const Icon = Config.icon;
                                            return (
                                                <button
                                                    key={level}
                                                    onClick={() => {
                                                        setSelectedLevel(level);
                                                        setIsLevelDropdownOpen(
                                                            false
                                                        );
                                                    }}
                                                    className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-all duration-200 ${
                                                        selectedLevel === level
                                                            ? "bg-gray-700/50"
                                                            : "hover:bg-gray-700/30"
                                                    } first:rounded-t-xl last:rounded-b-xl`}
                                                >
                                                    <div
                                                        className={`w-10 h-10 rounded-lg bg-gradient-to-r ${Config.color} flex items-center justify-center`}
                                                    >
                                                        <Icon className="w-5 h-5 text-white" />
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-medium">
                                                            {Config.name}
                                                        </div>
                                                        <div className="text-xs text-gray-400">
                                                            {Config.description}
                                                        </div>
                                                    </div>
                                                </button>
                                            );
                                        })}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Chat Area */}
            <main className="flex-1 overflow-hidden">
                <div className="h-full max-w-4xl mx-auto">
                    {messages.length === 0 ? (
                        <div className="h-full flex items-center justify-center p-8">
                            <div className="text-center max-w-xl">
                                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-purple-500/20 to-indigo-500/20 mb-6">
                                    <FiBook className="w-8 h-8 text-purple-400" />
                                </div>
                                <h2 className="text-2xl font-bold mb-4">
                                    Ask about Jharkhand Policies
                                </h2>
                                <p className="text-gray-400 mb-8 leading-relaxed">
                                    Get precise, cited responses tailored to
                                    your expertise level. Choose between
                                    General, Summary, or Technical responses.
                                </p>

                                <div className="grid grid-cols-4 gap-4 mt-8">
                                    {Object.entries(LevelConfig).map(
                                        ([level, config]) => (
                                            <div
                                                key={level}
                                                className={`p-4 rounded-xl border ${
                                                    selectedLevel ===
                                                    parseInt(level)
                                                        ? `border-purple-500/50 bg-purple-500/10`
                                                        : `border-gray-700/50 bg-gray-800/30`
                                                }`}
                                            >
                                                <div
                                                    className={`w-10 h-10 rounded-lg bg-gradient-to-r ${config.color} flex items-center justify-center mx-auto mb-3`}
                                                >
                                                    <config.icon className="w-5 h-5 text-white" />
                                                </div>
                                                <h3 className="font-medium mb-1">
                                                    Level {level}
                                                </h3>
                                                <p className="text-xs text-gray-400">
                                                    {config.description}
                                                </p>
                                            </div>
                                        )
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="h-full overflow-y-auto">
                            <div className="p-6 space-y-6">
                                {messages.map((m, idx) => (
                                    <MessageBubble key={idx} message={m} />
                                ))}
                                {loading && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="flex justify-start"
                                    >
                                        <div className="max-w-[80%]">
                                            <div className="flex items-center gap-3 mb-3">
                                                <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full flex items-center justify-center">
                                                    <FiBook className="w-4 h-4 text-white" />
                                                </div>
                                                <div className="text-sm font-medium text-gray-300">
                                                    Analyzing
                                                </div>
                                                <div className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded-full text-xs">
                                                    Lvl {selectedLevel}
                                                </div>
                                            </div>
                                            <div className="bg-gray-800/50 rounded-2xl px-4 py-4 border border-gray-700/50 backdrop-blur-sm">
                                                <div className="flex space-x-2">
                                                    {[0, 1, 2, 3].map((i) => (
                                                        <motion.div
                                                            key={i}
                                                            className="w-2 h-2 bg-purple-400 rounded-full"
                                                            animate={{
                                                                scale: [
                                                                    1, 1.5, 1,
                                                                ],
                                                            }}
                                                            transition={{
                                                                duration: 1.5,
                                                                repeat: Infinity,
                                                                delay: i * 0.2,
                                                            }}
                                                        />
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                                <div ref={endRef} />
                            </div>
                        </div>
                    )}
                </div>
            </main>

            {/* Input Area */}
            <footer className="border-t border-gray-700/50 bg-gray-900/80 backdrop-blur-xl p-6">
                <div className="max-w-4xl mx-auto">
                    <div className="flex gap-3 items-end">
                        <div className="flex-1 px-2.5 relative flex items-center rounded-2xl bg-gray-800/50 border border-gray-600/50 hover:border-purple-500/50 focus:ring-1 hover:ring-purple-500/30">
                            <textarea
                                ref={textareaRef}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={onKeyDown}
                                placeholder={`Ask a Level ${selectedLevel} question about Jharkhand policies...`}
                                rows={1}
                                style={{
                                    scrollbarWidth: "none",
                                    msOverflowStyle: "none",
                                }}
                                className="w-full resize-none rounded-2xl px-4 py-3 pr-12 outline-none text-white placeholder-gray-400 transition-all duration-200 backdrop-blur-sm"
                            />
                            <button
                                onClick={handleSend}
                                disabled={!canSend}
                                className="p-2.5 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-500 text-white hover:from-purple-600 hover:to-indigo-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-purple-500/20"
                            >
                                <FiSend className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                    <div className="mt-3 flex justify-between items-center text-xs text-gray-500">
                        <div className="flex items-center gap-2">
                            <div
                                className={`w-2 h-2 rounded-full ${getServerStatusColor()}`}
                            ></div>
                            <span>
                                {serverStatus?.status === "healthy"
                                    ? "Server operational"
                                    : serverStatus?.status === "warning"
                                    ? "Server warning"
                                    : "Server down"}
                            </span>
                        </div>
                        <span>
                            Press Enter to send, Shift+Enter for new line
                        </span>
                    </div>
                </div>
            </footer>
        </div>
    );
}

function MessageBubble({ message }: { message: Message }) {
    if (message.role === "user") {
        return (
            <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex justify-end"
            >
                <div className="max-w-[80%] bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-2xl rounded-br-md px-5 py-4 shadow-xl">
                    <div className="whitespace-pre-wrap break-words">
                        {message.content}
                    </div>
                </div>
            </motion.div>
        );
    }

    const LevelConfig = {
        0: {
            color: "from-green-500 to-emerald-500",
            name: "General",
            description: "Simple explanations",
        },
        1: {
            color: "from-blue-500 to-cyan-500",
            name: "Summary",
            description: "Concise overviews",
        },
        2: {
            color: "from-purple-500 to-indigo-500",
            name: "Technical",
            description: "Detailed analysis",
        },
        3: {
            color: "from-orange-500 to-yellow-500",
            name: "Auto",
            description: "Most suitable answer",
        },
    };

    const levelConfig =
        LevelConfig[message.level as keyof typeof LevelConfig] ||
        LevelConfig[3];

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex justify-start"
        >
            <div className="max-w-[80%]">
                <div className="flex items-center gap-3 mb-3">
                    <div
                        className={`w-8 h-8 bg-gradient-to-r ${levelConfig.color} rounded-full flex items-center justify-center`}
                    >
                        <FiBook className="w-4 h-4 text-white" />
                    </div>
                    <div>
                        <div className="text-sm font-medium text-gray-300">
                            Assistant
                        </div>
                        <div className="text-xs text-gray-500">
                            {levelConfig.description}
                        </div>
                    </div>
                    <div
                        className={`px-2 py-1 bg-gradient-to-r ${
                            levelConfig.color
                        }/20 text-${
                            levelConfig.color.split(" ")[1].split("-")[1]
                        }-300 rounded-full text-xs`}
                    >
                        {message.level === 3
                            ? "Auto"
                            : "Level " + message.level}
                    </div>
                </div>
                <div className="bg-gray-800/50 rounded-2xl px-5 py-4 border border-gray-700/50 backdrop-blur-sm shadow-xl">
                    <div className="whitespace-pre-wrap break-words text-gray-100 leading-relaxed">
                        {message.content || ""}
                    </div>

                    {/* Citations */}
                    {message.citations && message.citations.length > 0 && (
                        <div className="mt-5 pt-4 border-t border-gray-700/50">
                            <div className="flex items-center gap-2 mb-3">
                                <div className="w-6 h-6 bg-gradient-to-r from-gray-400 to-gray-300 rounded-lg flex items-center justify-center">
                                    <IoDocumentText className="w-3.5 h-3.5 text-gray-800" />
                                </div>
                                <span className="text-sm font-medium text-gray-300">
                                    Sources ({message.citations.length})
                                </span>
                            </div>
                            <div className="space-y-3">
                                {message.citations.map((c, i) => (
                                    <motion.div
                                        key={i}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: i * 0.1 }}
                                        className="text-sm p-4 bg-gray-700/30 rounded-xl border border-gray-600/30 hover:border-gray-500/50 transition-colors"
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="mt-0.5 flex-shrink-0">
                                                {c.source_file
                                                    .toLowerCase()
                                                    .endsWith(".pdf") ? (
                                                    <FaFilePdf className="w-5 h-5 text-red-400" />
                                                ) : (
                                                    <FiFileText className="w-5 h-5 text-blue-400" />
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="font-medium text-gray-200 truncate">
                                                    {c.source_file}
                                                </div>
                                                <div className="text-gray-400 text-xs mt-1 flex items-center gap-2">
                                                    <span>
                                                        Pages {c.page_start}-
                                                        {c.page_end}
                                                    </span>
                                                    <span>•</span>
                                                    <span className="flex items-center gap-1">
                                                        <div className="w-12 bg-gray-600 rounded-full h-1.5">
                                                            <div
                                                                className="bg-emerald-500 h-1.5 rounded-full"
                                                                style={{
                                                                    width: `${
                                                                        c.score *
                                                                        100
                                                                    }%`,
                                                                }}
                                                            ></div>
                                                        </div>
                                                        <span>
                                                            {(
                                                                c.score * 100
                                                            ).toFixed(1)}
                                                            %
                                                        </span>
                                                    </span>
                                                </div>
                                                {c.snippet && (
                                                    <div className="mt-3 text-gray-300 text-sm leading-relaxed bg-gray-800/40 p-3 rounded-lg">
                                                        &apos;{c.snippet}&apos;
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Prompt view */}
                {message.prompt && <PromptViewer prompt={message.prompt} />}
            </div>
        </motion.div>
    );
}

function PromptViewer({ prompt }: { prompt: string }) {
    const [open, setOpen] = useState(false);
    return (
        <div className="mt-4">
            <button
                onClick={() => setOpen((v) => !v)}
                className="flex items-center gap-2 text-xs text-gray-400 hover:text-gray-300 transition-colors group"
            >
                <div
                    className={`w-4 h-4 transition-transform duration-200 ${
                        open ? "rotate-180" : ""
                    } group-hover:scale-110`}
                >
                    {open ? (
                        <FiChevronUp className="w-full h-full" />
                    ) : (
                        <FiChevronDown className="w-full h-full" />
                    )}
                </div>
                {open ? "Hide system prompt" : "Show system prompt"}
            </button>
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="mt-2 overflow-hidden"
                    >
                        <div className="p-4 bg-gray-900 rounded-xl border border-gray-700/50 backdrop-blur-sm">
                            <div className="text-xs text-gray-400 mb-2 font-mono uppercase tracking-wider flex items-center gap-2">
                                <FiInfo className="w-3 h-3" />
                                System Prompt
                            </div>
                            <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap overflow-auto max-h-64 leading-5">
                                {prompt}
                            </pre>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
