import  { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { motion, AnimatePresence } from 'motion/react';
import {techBadges ,features,archPipeline} from '#/lib/demoData.ts'
import {
  Bot,
  Network,
  Github,
  Linkedin,
  FileText,
  ExternalLink,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { ThemeToggle } from '#/components/ThemeToggle';


export const Route = createFileRoute('/')({
  component: TheChatBotLandingPage,
});
export default function TheChatBotLandingPage() {
  const [activeArchNode, setActiveArchNode] = useState<number | null>(null);



  return (
    <div className="min-h-screen bg-background text-foreground font-sans antialiased selection:bg-primary selection:text-primary-foreground">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-6xl mx-auto flex h-14 items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <span className="font-semibold text-sm tracking-tight">
              TheChatBot
            </span>
            <span className="rounded-md bg-secondary px-2 py-0.5 text-xs font-mono text-muted-foreground border border-border">
              RAG v2.4
            </span>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-md text-xs font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-3 transition-colors"
            >
              <Github className="mr-2 h-3.5 w-3.5" />
              Source Code
            </a>
            <ThemeToggle/>
            <a
              href="login"
              className="inline-flex items-center justify-center rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-8 px-3 transition-colors"
            >
              Live Demo
              <ExternalLink className="ml-1.5 h-3 w-3" />
            </a>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 md:py-28 px-6 max-w-6xl mx-auto text-center border-b border-border">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/50 px-3 py-1 text-xs font-mono text-muted-foreground mb-6"
        >
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span>Production-Ready RAG Platform</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          className="text-4xl md:text-6xl font-bold tracking-tight max-w-3xl mx-auto leading-tight mb-6"
        >
          High-Density Vector Retrieval & Async Streaming
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="text-muted-foreground text-base md:text-lg max-w-2xl mx-auto mb-8 leading-relaxed"
        >
          An enterprise RAG system engineered with FastAPI, Cloudflare R2, VoyageAI, and hybrid vector indexes for low-latency contextual intelligence.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className="flex flex-wrap items-center justify-center gap-3"
        >
          <a
            href="#architecture"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 transition-colors"
          >
            System Architecture
            <ChevronRight className="ml-1 h-4 w-4" />
          </a>
          <a
            href="#contact"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 transition-colors"
          >
            Developer Overview
          </a>
        </motion.div>
      </section>

      {/* System Architecture Visualizer */}
      <section id="architecture" className="py-16 md:py-24 px-6 max-w-6xl mx-auto border-b border-border">
        <div className="mb-12">
          <h2 className="text-2xl font-bold tracking-tight mb-2">System Architecture</h2>
          <p className="text-muted-foreground text-sm">
            End-to-end cloud pipeline from document storage to low-latency token dispatch.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {archPipeline.map((node, index) => {
            const Icon = node.icon;
            const isActive = activeArchNode === node.id;

            return (
              <div
                key={node.id}
                onClick={() => setActiveArchNode(node.id)}
                className={`cursor-pointer rounded-lg border p-5 transition-colors relative ${
                  isActive
                    ? 'border-primary bg-accent/50'
                    : 'border-border bg-card hover:bg-accent/30'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-muted">
                    <Icon className="h-4 w-4 text-foreground" />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground">0{index + 1}</span>
                </div>
                
                <h3 className="font-semibold text-sm mb-1">{node.title}</h3>
                <div className="inline-block rounded bg-secondary px-2 py-0.5 text-[11px] font-mono text-secondary-foreground border border-border mb-3">
                  {node.tech}
                </div>
                <p className="text-xs text-muted-foreground leading-normal">{node.desc}</p>
              </div>
            );
          })}
        </div>

        <AnimatePresence>
          {activeArchNode && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-4 rounded-lg border border-border bg-muted/40 p-4 font-mono text-xs text-muted-foreground"
            >
              <div className="flex items-center justify-between border-b border-border pb-2 mb-2 text-foreground font-semibold">
                <span className="flex items-center gap-2">
                  <Network className="h-3.5 w-3.5" /> Pipeline Trace Log
                </span>
                <button
                  onClick={() => setActiveArchNode(null)}
                  className="text-muted-foreground hover:text-foreground text-[11px]"
                >
                  [Dismiss]
                </button>
              </div>
              <p>
                Stage {activeArchNode} initialized. Payload verified. Connection handshake latency &lt; 2ms.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* Feature & Benchmarks Section */}
      <section className="py-16 md:py-24 px-6 max-w-6xl mx-auto border-b border-border">
        <div className="mb-12">
          <h2 className="text-2xl font-bold tracking-tight mb-2">Performance & Engineering Features</h2>
          <p className="text-muted-foreground text-sm">
            Core capabilities engineered for enterprise scale, security, and low latency.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((feat, i) => {
            const Icon = feat.icon;
            return (
              <div
                key={i}
                className="rounded-lg border border-border bg-card p-5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-muted mb-4">
                    <Icon className="h-4 w-4 text-foreground" />
                  </div>
                  <h3 className="font-semibold text-sm mb-1.5">{feat.title}</h3>
                  <p className="text-xs text-muted-foreground leading-normal mb-6">{feat.desc}</p>
                </div>
                <div className="pt-3 border-t border-border">
                  <div className="text-xl font-bold text-foreground font-mono">{feat.metric}</div>
                  <div className="text-[10px] uppercase font-mono tracking-wider text-muted-foreground mt-0.5">
                    {feat.metricLabel}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Recruiter Overview & CTA */}
      <section id="contact" className="py-16 md:py-24 px-6 max-w-4xl mx-auto text-center">
        <div className="rounded-xl border border-border bg-card p-8 md:p-12">
          <h2 className="text-2xl font-bold tracking-tight mb-2">Recruiter & Engineering Overview</h2>
          <p className="text-muted-foreground text-sm max-w-xl mx-auto mb-6">
            Review technical source code, explore production deployments, or connect regarding software roles.
          </p>

          <div className="flex flex-wrap justify-center gap-1.5 mb-8">
            {techBadges.map((badge) => (
              <span
                key={badge}
                className="rounded-md border border-border bg-secondary px-2.5 py-1 text-xs font-mono text-secondary-foreground"
              >
                {badge}
              </span>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-md text-xs font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-4 transition-colors"
            >
              <Github className="mr-2 h-4 w-4" />
              GitHub
            </a>
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-md text-xs font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-4 transition-colors"
            >
              <Linkedin className="mr-2 h-4 w-4" />
              LinkedIn
            </a>
            <a
              href="/resume.pdf"
              download
              className="inline-flex items-center justify-center rounded-md text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 transition-colors"
            >
              <FileText className="mr-2 h-4 w-4" />
              Resume
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 px-6 border-t border-border text-center text-xs text-muted-foreground font-mono">
        © {new Date().getFullYear()} TheChatBot RAG Platform. Built with TanStack Router & Tailwind CSS.
      </footer>
    </div>
  );
}