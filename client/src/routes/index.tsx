import ThemeToggle from '#/components/ThemeToggle'
import { Button } from '#/components/ui/button'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({ component: App })

function App() {
  return (
    <main className="flex flex-col min-h-dvh items-center justify-center text-9xl">
      <h1>welcome to agentic chatbot</h1>
      <ThemeToggle />
      <Button>Click me</Button>
    </main>
  )
}
