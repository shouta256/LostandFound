import { useEffect, useState } from 'react'
import type { AuthSession } from './GoogleLogin'
import LandingPage from './LandingPage'
import ItemBrowser from './ItemBrowser'
import './App.css'

function App() {
  const [session, setSession] = useState<AuthSession | null>(null)

  useEffect(() => {
    if (!session) return
    const timeout = window.setTimeout(() => setSession(null), session.expires_in * 1000)
    return () => window.clearTimeout(timeout)
  }, [session])

  return session
    ? <ItemBrowser session={session} onSignOut={() => setSession(null)} />
    : <LandingPage onLogin={setSession} />
}

export default App
