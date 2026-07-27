import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router";
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
  status?: "complete" | "streaming" | "failed" | "cancelled";
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

export default function ChatPage() {
  const { thread_id } = useParams<{ thread_id: string }>();

  // Sidebar store to sync active thread & titles list
  const threads = useSidebarStore((state) => state.threads);
  const fetchThreads = useSidebarStore((state) => state.fetchThreads);
  const setActiveThreadId = useSidebarStore((state) => state.setActiveThreadId);

  const activeThread = threads.find((t) => t.id === thread_id);
  const title = activeThread ? activeThread.title : `Chat (${thread_id?.slice(0, 8) || ""})`;

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

  // Document upload state
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Copy state tracker
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Scroll ref
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Set active thread ID in store when route changes
  useEffect(() => {
    if (thread_id) {
      setActiveThreadId(thread_id);
    }
  }, [thread_id, setActiveThreadId]);

  // Load message history & model selection for current thread
  useEffect(() => {
    if (!thread_id) return;

    let isMounted = true;

    async function loadThreadData() {
      setIsLoadingHistory(true);
      setErrorMsg(null);

      try {
        // 1. Fetch message history from API Section 1.4: GET /v1/chat/base/get_messages/{thread_id}
        const historyRes = await api
          .get(`chat/base/get_messages/${thread_id}`)
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

      // 2. Fetch thread model selection from API Section 1.5: GET /v1/chat/base/{thread_id}/models
      try {
        const modelsRes = await api
          .get(`chat/base/${thread_id}/models`)
          .json<ModelSelectionResponse>();

        if (isMounted) {
          setCurrentModel(modelsRes.current_model || modelsRes.default_model || "");
          setAvailableModels(modelsRes.models || []);
        }
      } catch (err) {
        console.warn("Could not fetch models for thread:", err);
      }
    }

    loadThreadData();

    return () => {
      isMounted = false;
    };
  }, [thread_id]);

  // Handle LLM Model selection change
  const handleModelChange = async (newModel: string) => {
    if (!thread_id || newModel === currentModel) return;

    setIsUpdatingModel(true);
    try {
      // API Section 1.6: PATCH /v1/chat/base/{thread_id}/model
      await api.patch(`chat/base/${thread_id}/model`, {
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

  // Handle Document Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !thread_id) return;

    setIsUploadingDoc(true);
    setErrorMsg(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      // API Section 2.1: POST /v1/chat/{thread_id}/documents
      await api.post(`chat/${thread_id}/documents`, {
        body: formData,
      }).json();

      setUploadedFiles((prev) => [...prev, file.name]);
    } catch (err: any) {
      console.error("File upload error:", err);
      setErrorMsg("Failed to upload document. Maximum file size is 20MB.");
    } finally {
      setIsUploadingDoc(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // Handle Sending Prompt and Streaming Response
  const handleSendPrompt = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    const promptText = inputPrompt.trim();
    if (!promptText || !thread_id || isStreaming) return;

    // Clear input
    setInputPrompt("");
    setErrorMsg(null);

    const userMessageId = crypto.randomUUID();
    const assistantMessageId = crypto.randomUUID();

    // Optimistically update message history
    const userMsg: MessageItem = {
      id: userMessageId,
      thread_id,
      role: "user",
      content: promptText,
      status: "complete",
      created_at: new Date().toISOString(),
    };

    const initialAiMsg: MessageItem = {
      id: assistantMessageId,
      thread_id,
      role: "assistant",
      content: "",
      status: "streaming",
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, initialAiMsg]);
    setIsStreaming(true);

    try {
      // API Section 1.3: POST /v1/chat/base/{thread_id}
      const response = await api.post(`chat/base/${thread_id}`, {
        json: { prompt: promptText },
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error("Response body is not readable");

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
              setMessages((prevMsgs) => {
                return prevMsgs.map((msg) => {
                  if (msg.id === assistantMessageId) {
                    return {
                      ...msg,
                      content: msg.content + chunkText,
                    };
                  }
                  return msg;
                });
              });
            }
          } catch {
            // Raw string chunk fallback
            if (jsonStr !== "[DONE]") {
              setMessages((prevMsgs) => {
                return prevMsgs.map((msg) => {
                  if (msg.id === assistantMessageId) {
                    return {
                      ...msg,
                      content: msg.content + jsonStr,
                    };
                  }
                  return msg;
                });
              });
            }
          }
        }
      }

      // Complete status for assistant message
      setMessages((prevMsgs) =>
        prevMsgs.map((msg) =>
          msg.id === assistantMessageId ? { ...msg, status: "complete" } : msg
        )
      );

      // Refresh sidebar thread titles list (since backend auto-titles on first prompt)
      fetchThreads();
    } catch (err: any) {
      console.error("Streaming error:", err);
      setErrorMsg("An error occurred while receiving response stream.");
      setMessages((prevMsgs) =>
        prevMsgs.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content:
                  msg.content ||
                  "⚠️ Sorry, an error occurred while generating the response.",
                status: "failed",
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  // Copy text helper
  const handleCopyContent = (id: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Header */}
        <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/80 backdrop-blur-xs">
          <div className="flex items-center gap-2 min-w-0">
            <MobileSidebarTrigger />
            <h1 className="text-sm font-semibold text-foreground truncate flex items-center gap-2">
              <Sparkles className="size-4 text-primary shrink-0" />
              <span className="truncate">{title}</span>
            </h1>
          </div>

          <div className="flex items-center gap-2">
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
                    <span className="truncate max-w-[110px] md:max-w-[150px]">
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

            <ThemeToggle />
          </div>
        </header>

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
                      <div className="whitespace-pre-wrap leading-relaxed break-words font-sans">
                        {msg.content}
                        {!isUser && msg.status === "streaming" && !msg.content && (
                          <div className="flex items-center gap-1.5 text-muted-foreground text-xs py-1">
                            <Loader2 className="size-3.5 animate-spin text-primary" />
                            <span>Thinking...</span>
                          </div>
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

        {/* Uploaded Files Chips */}
        {uploadedFiles.length > 0 && (
          <div className="px-4 py-2 border-t border-border/60 bg-muted/20 flex items-center gap-2 overflow-x-auto max-w-3xl mx-auto w-full">
            <span className="text-[11px] font-medium text-muted-foreground shrink-0 flex items-center gap-1">
              <FileText className="size-3" /> Attached Context:
            </span>
            {uploadedFiles.map((fn, idx) => (
              <span
                key={idx}
                className="text-[11px] font-mono px-2 py-0.5 bg-accent/70 border border-border rounded-md text-foreground shrink-0"
              >
                {fn}
              </span>
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
              disabled={isUploadingDoc || isStreaming}
              onClick={() => fileInputRef.current?.click()}
              className="rounded-xl shrink-0 h-10 w-10 border-border text-muted-foreground hover:text-foreground"
              title="Attach Document (.pdf, .txt, .md, .csv, .docx)"
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
                placeholder={`Message ${title}...`}
                disabled={isStreaming}
                rows={1}
                className="w-full resize-none py-2.5 px-4 text-sm bg-muted/40 rounded-xl border border-border focus:outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground max-h-32 min-h-[40px]"
              />
            </div>

            {/* Send Button */}
            <Button
              type="submit"
              disabled={!inputPrompt.trim() || isStreaming}
              className="rounded-xl h-10 w-10 shrink-0"
              size="icon"
            >
              {isStreaming ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

