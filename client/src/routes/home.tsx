import { createFileRoute, redirect } from '@tanstack/react-router'
import { api } from '#/lib/KyClient'

export const Route = createFileRoute('/home')({
  component: RouteComponent,

  beforeLoad: async () => {
    try {
      await api.get('auth/me').json()
    } catch {
      throw redirect({
        to: '/login',
      })
    }
  },
})

function RouteComponent() {
  return <div>Hello "/(app)/home"!</div>
}

