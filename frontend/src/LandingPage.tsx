import { useRef } from 'react'
import GoogleLogin from './GoogleLogin'
import type { AuthSession } from './GoogleLogin'

type Props = {
  onLogin: (session: AuthSession) => void
}

const steps = [
  { title: 'Report it', description: 'Share what you lost or found and where you last saw it.' },
  { title: 'Search the listings', description: 'Browse campus listings to find a familiar item or help someone else.' },
  { title: 'Claim and pick up on campus', description: 'Submit a claim and arrange a campus pickup once it is approved.' },
]

export default function LandingPage({ onLogin }: Props) {
  const signIn = useRef<HTMLDivElement>(null)

  function focusSignIn() {
    const target = signIn.current
    if (!target) return
    target.focus({ preventScroll: true })
    target.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
      block: 'center',
    })
  }

  return (
    <div className="landing-page">
      <header className="landing-header">
        <div className="landing-container landing-header-content">
          <div className="brand">
            <span className="brand-icon" aria-hidden="true">⌕</span>
            <span>Lost &amp; Found</span>
          </div>
          <span className="landing-campus">Washburn University</span>
        </div>
      </header>

      <main className="landing-container landing-main">
        <section className="landing-hero" aria-labelledby="landing-title">
          <div className="landing-intro">
            <p className="eyebrow">YOUR CAMPUS. YOUR COMMUNITY.</p>
            <h1 id="landing-title">Good things find their way back.</h1>
            <p className="hero-description">
              Lost something? Found something? Connect with the Washburn community
              and help reunite people with their belongings.
            </p>
            <div id="sign-in" className="landing-sign-in" ref={signIn} tabIndex={-1} aria-label="Sign in">
              <GoogleLogin onLogin={onLogin} />
              <p className="landing-note">Use your Google account to view and report items.</p>
            </div>
          </div>
        </section>

        <section className="landing-how" aria-labelledby="landing-how-title">
          <p className="eyebrow">HOW IT WORKS</p>
          <h2 id="landing-how-title">A little help goes a long way.</h2>
          <ol className="landing-steps">
            {steps.map((step, index) => (
              <li className="landing-step" key={step.title}>
                <span className="landing-step-number" aria-hidden="true">0{index + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="landing-cta" aria-labelledby="landing-cta-title">
          <div>
            <h2 id="landing-cta-title">Lost something on campus?</h2>
            <p>Your next step could bring it a little closer to home.</p>
          </div>
          <button type="button" className="hero-button" onClick={focusSignIn}>
            Sign in to get started
          </button>
        </section>
      </main>

      <footer className="landing-container landing-footer">
        <span>Lost &amp; Found · Washburn University</span>
        <span>CM333 project</span>
      </footer>
    </div>
  )
}
