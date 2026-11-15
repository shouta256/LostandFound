import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AuthSession } from './GoogleLogin'
import { ApiError, apiRequest, errorMessage, type Item } from './api'

export default function ClaimSubmission({ item, session, onViewClaims }: {
  item: Item; session: AuthSession; onViewClaims?: () => void
}) {
  const [ownershipInformation, setOwnershipInformation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)

  if (item.type !== 'found' || item.status !== 'available' || item.created_by === session.user.id) return null

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const information = ownershipInformation.trim()
    if (!information || information.length > 2000) {
      setError('Ownership information is required and must be at most 2000 characters.')
      return
    }

    setBusy(true)
    setError('')
    try {
      await apiRequest('/claims', session.access_token, {
        method: 'POST',
        body: JSON.stringify({ item_id: item.id, ownership_information: information }),
      })
      setSubmitted(true)
      setOwnershipInformation('')
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.code === 'DUPLICATE_PENDING_CLAIM') {
        setError('You already have a pending claim for this item.')
      } else {
        setError(errorMessage(requestError))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="claim-submission" aria-labelledby="claim-submission-title">
      <h3 id="claim-submission-title">Claim this item</h3>
      <p>Describe details that help verify it belongs to you.</p>
      {submitted ? (
        <>
          <p className="claim-success" role="status">Claim submitted for review.</p>
          {onViewClaims && <button className="hero-button" type="button" onClick={onViewClaims}>View my claims</button>}
        </>
      ) : (
        <form className="claim-submission-form" onSubmit={submit}>
          <label htmlFor="ownership-information">Ownership information</label>
          <textarea
            id="ownership-information"
            value={ownershipInformation}
            maxLength={2000}
            required
            disabled={busy}
            onChange={event => setOwnershipInformation(event.target.value)}
          />
          <button className="hero-button" type="submit" disabled={busy}>
            {busy ? 'Submitting...' : 'Submit claim'}
          </button>
          {error && <p className="error-message" role="alert">{error}</p>}
        </form>
      )}
    </section>
  )
}
