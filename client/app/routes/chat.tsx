import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router";
import { Sidebar, MobileSidebarTrigger } from "@/components/sidebar";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useSidebarStore } from "@/lib/ZustandStore";
import { api } from "@/lib/kyClient";
import {
  Bot,
  Send,
  Sparkles,
  Paperclip,
  Loader2,
  Copy,
  Check,
  Cpu,
  FileText,
  AlertCircle,
  Square,
  Eye,
  Trash2,
  Database,
  X,
  Download,
  FolderOpen,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface MessageItem {
  id: string;
  thread_id?: string;
  role: "user" | "assistant" | "human" | "ai";
  content: string;
  status?: "complete" | "streaming" | "failed" | "cancelled" | string;
  created_at?: string;
}

export interface ModelItem {
  model: string;
  display_name?: string;
  description?: string;
  provider?: string;
}

export interface ModelSelectionResponse {
  current_model: string;
  default_model: string;
  models: (string | ModelItem)[];
}

export interface RagStrategyItem {
  id: string;
  display_name: string;
  description: string;
}

export interface RagStrategyResponse {
  current_strategy: string;
  default_strategy: string;
  strategies: RagStrategyItem[];
}

export interface DocumentItem {
  id: string;
  thread_id: string;
  filename: string;
  content_type: string;
  file_size_bytes: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string;
  created_at?: string;
  updated_at?: string;
}

export default function ChatPage() {
  const { thread_id } = useParams<{ thread_id?: string }>();
  const navigate = useNavigate();

  // Sidebar store to sync active thread & titles list
  const threads = useSidebarStore((state) => state.threads);
  const fetchThreads = useSidebarStore((state) => state.fetchThreads);
  const createThread = useSidebarStore((state) => state.createThread);
  const setActiveThreadId = useSidebarStore((state) => state.setActiveThreadId);

  const activeThread = threads.find((t) => t.id === thread_id);
  const title = activeThread ? activeThread.title : thread_id ? `Chat (${thread_id.slice(0, 8)})` : "New Conversation";

  // Local state
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Model selection state
  const [currentModel, setCurrentModel] = useState<string>("");
  const [availableModels, setAvailableModels] = useState<(string | ModelItem)[]>([]);
  const [isUpdatingModel, setIsUpdatingModel] = useState(false);

  // RAG strategy selection state
  const [currentStrategy, setCurrentStrategy] = useState<string>("basic");
  const [availableStrategies, setAvailableStrategies] = useState<RagStrategyItem[]>([]);
  const [isUpdatingStrategy, setIsUpdatingStrategy] = useState(false);

  // Documents state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [ingestingDocId, setIngestingDocId] = useState<string | null>(null);
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);
  const [showDocPanel, setShowDocPanel] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stream reader & copy tracker refs
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Scroll ref
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Ref to skip message history overwrite when a thread is lazily created during prompt submit
  const newlyCreatedThreadIdRef = useRef<string | null>(null);

  // Fetch thread document list: GET /v2/thread/{thread_id}/docs
  const fetchDocuments = async (targetThreadId?: string) => {
    const activeDocThreadId = targetThreadId || thread_id;
    if (!activeDocThreadId) {
      setDocuments([]);
      return;
    }
    setIsLoadingDocs(true);
    try {
      const res = await api.get(`thread/${activeDocThreadId}/docs`).json<{ documents: DocumentItem[] }>();
      setDocuments(res.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents for thread:", err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  // Set active thread ID in store & load history/models/docs when route changes
  useEffect(() => {
    if (!thread_id) {
      setActiveThreadId(null);
      setMessages([]);
      setDocuments([]);
      setIsLoadingHistory(false);
      return;
    }

    setActiveThreadId(thread_id);

    if (newlyCreatedThreadIdRef.current === thread_id) {
      newlyCreatedThreadIdRef.current = null;
      setIsLoadingHistory(false);
      fetchDocuments();
      return;
    }

    let isMounted = true;

    async function loadThreadData() {
      setIsLoadingHistory(true);
      setErrorMsg(null);

      try {
        // 1. Fetch message history: GET /v2/thread/{thread_id}/messages
        const historyRes = await api
          .get(`thread/${thread_id}/messages`)
          .json<{ messages: MessageItem[] }>();

        if (isMounted) {
          setMessages(historyRes.messages || []);
        }
      } catch (err: any) {
        console.error("Error loading chat history:", err);
        if (isMounted) {
          setErrorMsg("Failed to load message history for this thread.");
        }
      } finally {
        if (isMounted) {
          setIsLoadingHistory(false);
        }
      }

      // 2. Fetch thread model selection: GET /v2/thread/{thread_id}/models
      try {
        const modelsRes = await api
          .get(`thread/${thread_id}/models`)
          .json<ModelSelectionResponse>();

        if (isMounted) {
          setCurrentModel(modelsRes.current_model || modelsRes.default_model || "");
          setAvailableModels(modelsRes.models || []);
        }
      } catch (err) {
        console.warn("Could not fetch models for thread:", err);
      }

      // 3. Fetch thread RAG strategy selection: GET /v2/thread/{thread_id}/strategies
      try {
        const stratRes = await api
          .get(`thread/${thread_id}/strategies`)
          .json<RagStrategyResponse>();

        if (isMounted) {
          setCurrentStrategy(stratRes.current_strategy || stratRes.default_strategy || "basic");
          setAvailableStrategies(stratRes.strategies || []);
        }
      } catch (err) {
        console.warn("Could not fetch RAG strategies for thread:", err);
      }

      // 4. Fetch thread document list: GET /v2/thread/{thread_id}/docs
      fetchDocuments();
    }

    loadThreadData();

    return () => {
      isMounted = false;
    };
  }, [thread_id, setActiveThreadId]);

  // Handle LLM Model selection change: PATCH /v2/thread/{thread_id}/model
  const handleModelChange = async (newModel: string) => {
    if (!thread_id || newModel === currentModel) return;

    setIsUpdatingModel(true);
    try {
      await api.patch(`thread/${thread_id}/model`, {
        json: { model: newModel },
      }).json();

      setCurrentModel(newModel);
    } catch (err: any) {
      console.error("Failed to update thread model:", err);
      setErrorMsg("Failed to change LLM model.");
    } finally {
      setIsUpdatingModel(false);
    }
  };

  // Handle RAG Strategy selection change: PATCH /v2/thread/{thread_id}/strategy
  const handleStrategyChange = async (newStrategy: string) => {
    if (!thread_id || newStrategy === currentStrategy) return;

    setIsUpdatingStrategy(true);
    try {
      await api.patch(`thread/${thread_id}/strategy`, {
        json: { strategy: newStrategy },
      }).json();

      setCurrentStrategy(newStrategy);
    } catch (err: any) {
      console.error("Failed to update thread RAG strategy:", err);
      setErrorMsg("Failed to change RAG strategy.");
    } finally {
      setIsUpdatingStrategy(false);
    }
  };

  // Handle Document Upload: POST /v2/thread/{thread_id}/upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !thread_id) return;

    setIsUploadingDoc(true);
    setErrorMsg(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      await api.post(`thread/${thread_id}/upload`, {
        body: formData,
      }).json();

      // Refresh documents list
      await fetchDocuments();
    } catch (err: any) {
      console.error("File upload error:", err);
      setErrorMsg("Failed to upload document. Maximum file size is 20MB (.pdf, .txt, .md, .csv, .docx).");
    } finally {
      setIsUploadingDoc(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // Handle Show / Download Document: GET /v2/thread/{thread_id}/docs/{document_id}
  const handleShowDoc = async (doc: DocumentItem) => {
    if (!thread_id) return;
    setDownloadingDocId(doc.id);
    try {
      const response = await api.get(`thread/${thread_id}/docs/${doc.id}`);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      // Trigger download/view in browser
      const downloadAnchor = document.createElement("a");
      downloadAnchor.href = blobUrl;
      downloadAnchor.download = doc.filename;
      downloadAnchor.target = "_blank";
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      document.body.removeChild(downloadAnchor);

      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 10000);
    } catch (err) {
      console.error("Failed to show/download document:", err);
      setErrorMsg(`Could not download or open ${doc.filename}.`);
    } finally {
      setDownloadingDocId(null);
    }
  };

  // Handle Document Vector Ingestion: POST /v2/thread/{thread_id}/docs/{document_id}/ingest
  const handleIngestDoc = async (docId: string) => {
    if (!thread_id) return;
    setIngestingDocId(docId);
    setErrorMsg(null);

    try {
      await api.post(`thread/${thread_id}/docs/${docId}/ingest`).json();
      await fetchDocuments();
    } catch (err: any) {
      console.error("Document ingestion error:", err);
      let errorDetail = "Failed to process document into vector database.";
      try {
        const errorJson = await err.response.json();
        if (errorJson?.detail) {
          errorDetail = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {}
      setErrorMsg(errorDetail);
    } finally {
      setIngestingDocId(null);
    }
  };

  // Handle Delete Document: DELETE /v2/thread/{thread_id}/docs/{doc_id}
  const handleDeleteDoc = async (docId: string) => {
    if (!thread_id) return;

    try {
      await api.delete(`thread/${thread_id}/docs/${docId}`).json();
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      console.error("Failed to delete document:", err);
      setErrorMsg("Failed to delete document.");
    }
  };

  // Handle Stop Generation Stream: POST /v2/chat/{thread_id}/stop
  const handleStopGeneration = async () => {
    if (!thread_id) return;

    try {
      // Cancel client-side reader stream
      if (readerRef.current) {
        await readerRef.current.cancel().catch(() => {});
        readerRef.current = null;
      }

      // Send stop request to server: POST /v2/chat/{thread_id}/stop
      await api.post(`chat/${thread_id}/stop`).json();

      setMessages((prevMsgs) =>
        prevMsgs.map((msg) =>
          msg.status === "streaming" ? { ...msg, status: "cancelled" } : msg
        )
      );
    } catch (err) {
      console.error("Error stopping generation stream:", err);
    } finally {
      setIsStreaming(false);
    }
  };

  // Handle Sending Prompt and Streaming Response: POST /v2/chat/{thread_id}
  const handleSendPrompt = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    const promptText = inputPrompt.trim();
    if (!promptText || isStreaming) return;

    // Clear input
    setInputPrompt("");
    setErrorMsg(null);

    let activeId = thread_id;

    // Lazy Thread Creation: create thread on first message if on /chat
    if (!activeId) {
      const newThreadId = await createThread();
      if (!newThreadId) {
        setErrorMsg("Failed to create a new chat thread. Please try again.");
        return;
      }
      activeId = newThreadId;
      newlyCreatedThreadIdRef.current = activeId;
      navigate(`/chat/${activeId}`, { replace: true });
    }

    const userMessageId = crypto.randomUUID();
    const assistantMessageId = crypto.randomUUID();

    // Optimistically update message history
    const userMsg: MessageItem = {
      id: userMessageId,
      thread_id: activeId,
      role: "user",
      content: promptText,
      status: "complete",
      created_at: new Date().toISOString(),
    };

    const initialAiMsg: MessageItem = {
      id: assistantMessageId,
      thread_id: activeId,
      role: "assistant",
      content: "",
      status: "streaming",
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, initialAiMsg]);
    setIsStreaming(true);

    try {
      // API: POST /v2/chat/{activeId}
      const response = await api.post(`chat/${activeId}`, {
        json: {
          prompt: promptText,
          llm_model: currentModel || undefined,
          rag_strategy: currentStrategy || undefined,
        },
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error("Response body is not readable");
      readerRef.current = reader;

      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep potential incomplete line at end of array in buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;

          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const parsed = JSON.parse(jsonStr);
            let chunkText = "";

            if (typeof parsed === "string") {
              chunkText = parsed;
            } else if (parsed && typeof parsed === "object") {
              if (parsed.type === "ai" && parsed.content) {
                chunkText = parsed.content;
              } else if (parsed.content) {
                chunkText = parsed.content;
              }
            }

            if (chunkText) {
              setMessages((prevMsgs) =>
                prevMsgs.map((msg) => {
                  if (msg.id === assistantMessageId) {
                    return {
                      ...msg,
                      content: msg.content + chunkText,
                    };
                  }
                  return msg;
                })
              );
            }
          } catch {
            // Raw string chunk fallback
            if (jsonStr !== "[DONE]") {
              setMessages((prevMsgs) =>
                prevMsgs.map((msg) => {
                  if (msg.id === assistantMessageId) {
                    return {
                      ...msg,
                      content: msg.content + jsonStr,
                    };
                  }
                  return msg;
                })
              );
            }
          }
        }
      }

      // Complete status for assistant message
      setMessages((prevMsgs) =>
        prevMsgs.map((msg) =>
          msg.id === assistantMessageId && msg.status !== "cancelled"
            ? { ...msg, status: "complete" }
            : msg
        )
      );

      // Refresh sidebar thread titles list (since backend auto-titles on prompt)
      fetchThreads();
    } catch (err: any) {
      if (err.name === "AbortError" || err.message?.includes("cancel")) {
        console.log("Stream reader cancelled by user");
        return;
      }
      console.error("Streaming error:", err);
      setErrorMsg("An error occurred while receiving response stream.");
      setMessages((prevMsgs) =>
        prevMsgs.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content:
                  msg.content ||
                  "⚠️ Sorry, an error occurred while generating response.",
                status: "failed",
              }
            : msg
        )
      );
    } finally {
      readerRef.current = null;
      setIsStreaming(false);
    }
  };

  // Copy text helper
  const handleCopyContent = (id: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* Header */}
        <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/80 backdrop-blur-xs z-10">
          <div className="flex items-center gap-2 min-w-0">
            <MobileSidebarTrigger />
            <h1 className="text-sm font-semibold text-foreground truncate flex items-center gap-2">
              <Sparkles className="size-4 text-primary shrink-0" />
              <span className="truncate">{title}</span>
            </h1>
          </div>

          <div className="flex items-center gap-2">
            {/* Documents Drawer Toggle Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDocPanel(!showDocPanel)}
              className="h-8 text-xs gap-1.5 px-2.5 rounded-lg border border-border bg-muted/20 hover:bg-accent flex items-center text-foreground"
              title="View Thread Documents"
            >
              <FolderOpen className="size-3.5 text-primary" />
              <span className="hidden sm:inline">Docs</span>
              {documents.length > 0 && (
                <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-primary/20 text-primary font-mono text-[10px] font-bold">
                  {documents.length}
                </span>
              )}
            </Button>

            {/* Model Selector Dropdown */}
            {availableModels.length > 0 && (() => {
              const currentModelObj = availableModels.find(
                (m) => (typeof m === "string" ? m : m.model) === currentModel
              );
              const currentDisplayName =
                typeof currentModelObj === "string"
                  ? currentModelObj
                  : currentModelObj?.display_name || currentModel || "Select Model";

              return (
                <DropdownMenu>
                  <DropdownMenuTrigger
                    disabled={isUpdatingModel}
                    className="h-8 text-xs font-mono gap-1.5 px-2.5 rounded-lg border border-border bg-muted/30 hover:bg-accent flex items-center justify-between text-foreground disabled:opacity-50"
                  >
                    <Cpu className="size-3.5 text-primary" />
                    <span className="truncate max-w-27.5 md:max-w-37.5">
                      {currentDisplayName}
                    </span>
                    {isUpdatingModel ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <span className="text-muted-foreground text-[10px]">▼</span>
                    )}
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <div className="px-2 py-1.5 text-[11px] font-semibold text-muted-foreground">
                      Available LLMs
                    </div>
                    {availableModels.map((m) => {
                      const modelSlug = typeof m === "string" ? m : m.model;
                      const modelLabel = typeof m === "string" ? m : m.display_name || m.model;
                      const modelDesc = typeof m === "string" ? null : m.description;

                      return (
                        <DropdownMenuItem
                          key={modelSlug}
                          onClick={() => handleModelChange(modelSlug)}
                          className="text-xs flex flex-col items-start justify-between cursor-pointer py-1.5"
                        >
                          <div className="flex items-center justify-between w-full font-medium font-mono">
                            <span>{modelLabel}</span>
                            {modelSlug === currentModel && (
                              <Check className="size-3.5 text-primary ml-2 shrink-0" />
                            )}
                          </div>
                          {modelDesc && (
                            <span className="text-[10px] text-muted-foreground font-sans line-clamp-1 font-normal">
                              {modelDesc}
                            </span>
                          )}
                        </DropdownMenuItem>
                      );
                    })}
                  </DropdownMenuContent>
                </DropdownMenu>
              );
            })()}

            {/* RAG Strategy Selector Dropdown */}
            {availableStrategies.length > 0 && (() => {
              const currentStratObj = availableStrategies.find(
                (s) => s.id === currentStrategy
              );
              const currentDisplayName =
                currentStratObj?.display_name || currentStrategy || "RAG Strategy";

              return (
                <DropdownMenu>
                  <DropdownMenuTrigger
                    disabled={isUpdatingStrategy}
                    className="h-8 text-xs font-mono gap-1.5 px-2.5 rounded-lg border border-border bg-muted/30 hover:bg-accent flex items-center justify-between text-foreground disabled:opacity-50"
                    title="Select RAG Strategy"
                  >
                    <SlidersHorizontal className="size-3.5 text-primary" />
                    <span className="truncate max-w-24 md:max-w-36">
                      {currentDisplayName}
                    </span>
                    {isUpdatingStrategy ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <span className="text-muted-foreground text-[10px]">▼</span>
                    )}
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-64">
                    <div className="px-2 py-1.5 text-[11px] font-semibold text-muted-foreground flex items-center gap-1.5">
                      <SlidersHorizontal className="size-3 text-primary" />
                      <span>RAG Strategies</span>
                    </div>
                    {availableStrategies.map((s) => (
                      <DropdownMenuItem
                        key={s.id}
                        onClick={() => handleStrategyChange(s.id)}
                        className="text-xs flex flex-col items-start justify-between cursor-pointer py-1.5"
                      >
                        <div className="flex items-center justify-between w-full font-medium font-mono">
                          <span>{s.display_name}</span>
                          {s.id === currentStrategy && (
                            <Check className="size-3.5 text-primary ml-2 shrink-0" />
                          )}
                        </div>
                        {s.description && (
                          <span className="text-[10px] text-muted-foreground font-sans line-clamp-2 font-normal mt-0.5">
                            {s.description}
                          </span>
                        )}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              );
            })()}

            <ThemeToggle />
          </div>
        </header>

        {/* Slide-out Documents Drawer */}
        {showDocPanel && (
          <div className="absolute right-0 top-14 bottom-0 w-80 sm:w-96 bg-card/95 border-l border-border backdrop-blur-md z-30 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="size-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Thread Documents</h3>
              </div>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => setShowDocPanel(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="size-4" />
              </Button>
            </div>

            {/* Document List Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {isLoadingDocs ? (
                <div className="flex items-center justify-center py-10 text-muted-foreground text-xs gap-2">
                  <Loader2 className="size-4 animate-spin text-primary" />
                  <span>Loading documents...</span>
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-12 space-y-3">
                  <div className="size-12 rounded-full bg-muted flex items-center justify-center mx-auto text-muted-foreground">
                    <FolderOpen className="size-6" />
                  </div>
                  <p className="text-xs text-muted-foreground">No documents uploaded to this thread yet.</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-xs gap-1.5"
                  >
                    <Paperclip className="size-3.5" />
                    <span>Upload Document</span>
                  </Button>
                </div>
              ) : (
                documents.map((doc) => {
                  const isPdf = doc.content_type === "application/pdf";
                  const isPending = doc.status === "PENDING";
                  const isProcessing = doc.status === "PROCESSING" || ingestingDocId === doc.id;
                  const isCompleted = doc.status === "COMPLETED";

                  return (
                    <div
                      key={doc.id}
                      className="p-3 rounded-xl border border-border bg-background/50 space-y-2 hover:border-primary/30 transition-colors shadow-2xs"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-foreground truncate" title={doc.filename}>
                            {doc.filename}
                          </p>
                          <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                            {formatFileSize(doc.file_size_bytes)} • {doc.content_type.split("/")[1] || "file"}
                          </p>
                        </div>
                        {/* Status Badge */}
                        <span
                          className={`text-[9px] font-mono font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider shrink-0 ${
                            isCompleted
                              ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                              : isProcessing
                              ? "bg-amber-500/10 text-amber-500 border border-amber-500/20 animate-pulse"
                              : isPending
                              ? "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                              : "bg-destructive/10 text-destructive border border-destructive/20"
                          }`}
                        >
                          {doc.status}
                        </span>
                      </div>

                      {/* Action Buttons: Show Doc, Ingest RAG, Delete */}
                      <div className="flex items-center justify-between pt-2 border-t border-border/40 text-xs">
                        <Button
                          variant="ghost"
                          size="xs"
                          disabled={downloadingDocId === doc.id}
                          onClick={() => handleShowDoc(doc)}
                          className="h-7 text-[11px] gap-1 px-2 text-primary hover:bg-primary/10"
                          title="Show / Download Document"
                        >
                          {downloadingDocId === doc.id ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Eye className="size-3" />
                          )}
                          <span>Show Doc</span>
                        </Button>

                        <div className="flex items-center gap-1">
                          {isPdf && !isCompleted && (
                            <Button
                              variant="outline"
                              size="xs"
                              disabled={isProcessing}
                              onClick={() => handleIngestDoc(doc.id)}
                              className="h-7 text-[10px] gap-1 px-2 border-primary/40 text-foreground hover:bg-primary/10"
                              title="Chunk, embed & vector-index document for RAG"
                            >
                              {isProcessing ? (
                                <Loader2 className="size-3 animate-spin text-primary" />
                              ) : (
                                <Database className="size-3 text-primary" />
                              )}
                              <span>{isProcessing ? "Ingesting..." : "Vector Index"}</span>
                            </Button>
                          )}

                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => handleDeleteDoc(doc.id)}
                            className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10 p-0"
                            title="Delete Document"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Chat Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          <div className="max-w-3xl mx-auto space-y-6">
            {/* Error Notification */}
            {errorMsg && (
              <div className="p-3.5 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center justify-between gap-2 shadow-xs">
                <div className="flex items-center gap-2">
                  <AlertCircle className="size-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setErrorMsg(null)}
                  className="h-6 text-[10px] px-2 text-destructive hover:bg-destructive/20"
                >
                  Dismiss
                </Button>
              </div>
            )}

            {/* History Loading Skeleton */}
            {isLoadingHistory ? (
              <div className="space-y-4 py-8">
                <div className="flex items-center justify-center gap-2 text-muted-foreground text-xs">
                  <Loader2 className="size-4 animate-spin text-primary" />
                  <span>Retrieving conversation history...</span>
                </div>
              </div>
            ) : messages.length === 0 ? (
              /* Empty State Prompt Suggestions */
              <div className="py-16 text-center space-y-6">
                <div className="size-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto shadow-inner">
                  <Bot className="size-7" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-lg font-semibold text-foreground">
                    Start a new conversation
                  </h3>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                    Type a message below or pick a sample prompt to start streaming responses.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-md mx-auto text-left pt-2">
                  {[
                    "What features are included in FastAPI RAG engine?",
                    "Explain SSE streaming with chunked JSON payloads.",
                    "How do vector indexes optimize LLM context retrieval?",
                    "Draft an API specification for file upload ingestion.",
                  ].map((samplePrompt) => (
                    <button
                      key={samplePrompt}
                      onClick={() => {
                        setInputPrompt(samplePrompt);
                      }}
                      className="p-3 rounded-xl border border-border bg-card/60 hover:bg-accent/50 text-xs text-foreground text-left transition-all shadow-2xs hover:border-primary/40"
                    >
                      {samplePrompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Message List */
              messages.map((msg) => {
                const isUser = msg.role === "user" || msg.role === "human";
                const isCancelled = msg.status === "cancelled";

                return (
                  <div
                    key={msg.id}
                    className={`flex items-start gap-3 ${
                      isUser ? "flex-row-reverse" : "flex-row"
                    }`}
                  >
                    {/* Avatar */}
                    <div
                      className={`size-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 shadow-2xs ${
                        isUser
                          ? "bg-primary/20 text-primary"
                          : "bg-sidebar-border text-foreground border border-border"
                      }`}
                    >
                      {isUser ? "U" : <Bot className="size-4" />}
                    </div>

                    {/* Message Bubble */}
                    <div
                      className={`relative group max-w-xl text-sm p-4 rounded-2xl ${
                        isUser
                          ? "bg-primary text-primary-foreground rounded-tr-xs shadow-2xs"
                          : "bg-card border border-border text-foreground rounded-tl-xs shadow-2xs space-y-2"
                      }`}
                    >
                      {/* Message Content */}
                      <div className="whitespace-pre-wrap leading-relaxed wrap-break-word font-sans">
                        {msg.content}
                        {!isUser && msg.status === "streaming" && !msg.content && (
                          <div className="flex items-center gap-1.5 text-muted-foreground text-xs py-1">
                            <Loader2 className="size-3.5 animate-spin text-primary" />
                            <span>Thinking...</span>
                          </div>
                        )}
                        {isCancelled && (
                          <span className="inline-block mt-2 text-xs italic text-amber-500 font-mono">
                            [Generation stopped by user]
                          </span>
                        )}
                      </div>

                      {/* Copy Action for AI Messages */}
                      {!isUser && msg.content && (
                        <div className="flex items-center justify-end pt-1 gap-2 border-t border-border/40 text-[11px] text-muted-foreground">
                          <button
                            onClick={() => handleCopyContent(msg.id, msg.content)}
                            className="inline-flex items-center gap-1 hover:text-foreground transition-colors py-0.5 px-1.5 rounded hover:bg-muted/50"
                            title="Copy message"
                          >
                            {copiedId === msg.id ? (
                              <>
                                <Check className="size-3 text-green-500" />
                                <span className="text-green-500 font-medium">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="size-3" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Uploaded Documents Context Bar */}
        {documents.length > 0 && (
          <div className="px-4 py-2 border-t border-border/60 bg-muted/20 flex items-center gap-2 overflow-x-auto max-w-3xl mx-auto w-full">
            <span className="text-[11px] font-medium text-muted-foreground shrink-0 flex items-center gap-1">
              <FileText className="size-3 text-primary" /> Thread Context:
            </span>
            {documents.map((doc) => (
              <button
                key={doc.id}
                onClick={() => handleShowDoc(doc)}
                className="text-[11px] font-mono px-2 py-0.5 bg-accent/70 hover:bg-accent border border-border rounded-md text-foreground shrink-0 flex items-center gap-1.5 transition-colors"
                title={`Click to view/download ${doc.filename}`}
              >
                <span>{doc.filename}</span>
                <Download className="size-2.5 text-muted-foreground" />
              </button>
            ))}
          </div>
        )}

        {/* Bottom Input Area */}
        <div className="p-4 border-t border-border bg-background">
          <form
            onSubmit={handleSendPrompt}
            className="max-w-3xl mx-auto flex items-end gap-2"
          >
            {/* File Upload Button */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.txt,.md,.csv,.docx"
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={!thread_id || isUploadingDoc || isStreaming}
              onClick={() => fileInputRef.current?.click()}
              className="rounded-xl shrink-0 h-10 w-10 border-border text-muted-foreground hover:text-foreground disabled:opacity-50"
              title={!thread_id ? "Start a conversation to upload documents" : "Attach Document (.pdf, .txt, .md, .csv, .docx)"}
            >
              {isUploadingDoc ? (
                <Loader2 className="size-4 animate-spin text-primary" />
              ) : (
                <Paperclip className="size-4" />
              )}
            </Button>

            {/* Prompt Input Textarea */}
            <div className="flex-1 relative">
              <textarea
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendPrompt();
                  }
                }}
                placeholder={thread_id ? `Message ${title}...` : "Send a message..."}
                disabled={isStreaming}
                rows={1}
                className="w-full resize-none py-2.5 px-4 text-sm bg-muted/40 rounded-xl border border-border focus:outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground max-h-32 min-h-10"
              />
            </div>

            {/* Stop Generation OR Send Button */}
            {isStreaming ? (
              <Button
                type="button"
                onClick={handleStopGeneration}
                variant="destructive"
                className="rounded-xl h-10 px-3.5 shrink-0 gap-1.5 font-medium text-xs shadow-xs animate-pulse"
                title="Stop Generation Stream"
              >
                <Square className="size-3.5 fill-current" />
                <span>Stop</span>
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={!inputPrompt.trim()}
                className="rounded-xl h-10 w-10 shrink-0"
                size="icon"
              >
                <Send className="size-4" />
              </Button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
