import { useEffect, useRef, useState } from 'react'

export type AuthSession = {
  access_token: string
  token_type: 'Bearer'
  expires_in: number
  user: { id: string; email: string; name: string | null; role: 'student' | 'team_member' }
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: { client_id: string; callback: (response: { credential: string }) => void }) => void
          renderButton: (element: HTMLElement, options: {
            type: string
            theme: string
            size: string
            shape: string
            text: string
            logo_alignment: string
            locale: string
            width: number
          }) => void
          disableAutoSelect: () => void
        }
      }
    }
  }
}

type Props = { onLogin: (session: AuthSession) => void }
const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function GoogleLogin({ onLogin }: Props) {
  const button = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!clientId) return
    const controller = new AbortController()
    let pending = false

    async function signIn({ credential }: { credential: string }) {
      if (pending || controller.signal.aborted) return
      pending = true
      setBusy(true)
      setError('')
      try {
        const response = await fetch('/api/v1/auth/google', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id_token: credential }),
          signal: controller.signal,
        })
        if (!response.ok) throw new Error('Unable to sign in. Please try again.')
        const result: AuthSession = await response.json()
        if (!controller.signal.aborted) onLogin(result)
      } catch (error) {
        if (!controller.signal.aborted) {
          setError(error instanceof Error ? error.message : 'Unable to sign in.')
        }
      } finally {
        pending = false
        if (!controller.signal.aborted) setBusy(false)
      }
    }

    function renderButton() {
      if (controller.signal.aborted || !window.google || !button.current) return
      window.google.accounts.id.initialize({ client_id: clientId, callback: signIn })
      window.google.accounts.id.renderButton(button.current, {
        type: 'standard',
        theme: 'filled_black',
        size: 'large',
        shape: 'pill',
        text: 'signin_with',
        logo_alignment: 'left',
        locale: 'en',
        width: 280,
      })
    }

    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = renderButton
    script.onerror = () => {
      if (!controller.signal.aborted) setError('Google sign-in could not load. Please reload the page.')
    }
    if (window.google) renderButton()
    else document.head.appendChild(script)

    const container = button.current
    return () => {
      controller.abort()
      script.remove()
      container?.replaceChildren()
    }
  }, [onLogin])

  return (
    <section className="login" aria-label="Account">
      {!clientId && <p>Google sign-in is not available yet.</p>}
      <div ref={button} hidden={busy} />
      {busy && <p role="status">Signing in…</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
