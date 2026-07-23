import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/chat/$thread_id')({
  component: RouteComponent,
})

function RouteComponent() {
  const { thread_id } = Route.useParams()
  return <div>Hello "/chat/{thread_id}"!</div>
}
