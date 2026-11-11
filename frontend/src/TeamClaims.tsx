import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, apiRequest, errorMessage } from './api'
import type { ClaimDetail, ClaimPage, Item, Pickup } from './api'

const LIMIT = 20
const decisionMessages: Record<string, string> = {
  FORBIDDEN: 'You cannot review this claim (you may be the claimant).',
  CLAIM_ALREADY_DECIDED: 'This claim was already decided.',
  CLAIM_APPROVAL_CONFLICT: 'Another claim for this item is already approved, or the item is no longer available.',
}

function dateTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : 'Not reviewed'
}

type ItemCache = Map<string, Promise<Item | null>>

function cachedItem(cache: ItemCache, id: string, token: string) {
  let request = cache.get(id)
  if (!request) {
    // Drop failed lookups so a later view can retry them.
    request = apiRequest<Item>(`/items/${id}`, token).catch(() => {
      cache.delete(id)
      return null
    })
    cache.set(id, request)
  }
  return request
}

export default function TeamClaims({ token }: { token: string }) {
  const [claimId, setClaimId] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [cache] = useState<ItemCache>(() => new Map())

  return claimId ? (
    <ClaimReview key={claimId} id={claimId} token={token} cache={cache} onBack={() => setClaimId(null)} />
  ) : (
    <ClaimList token={token} offset={offset} setOffset={setOffset} cache={cache} onSelect={setClaimId} />
  )
}

function ClaimList({ token, offset, setOffset, cache, onSelect }: {
  token: string
  offset: number
  setOffset: (offset: number) => void
  cache: ItemCache
  onSelect: (id: string) => void
}) {
  const [page, setPage] = useState<ClaimPage | null>(null)
  const [names, setNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setError('')
      setPage(null)
      try {
        const result = await apiRequest<ClaimPage>(`/claims?limit=${LIMIT}&offset=${offset}`, token, { signal: controller.signal })
        if (controller.signal.aborted) return
        setPage(result)
        setLoading(false)
        const ids = [...new Set(result.data.map(claim => claim.item_id))]
        await Promise.all(ids.map(async id => {
          const item = await cachedItem(cache, id, token)
          if (!controller.signal.aborted) setNames(previous => ({ ...previous, [id]: item?.name ?? 'Unknown item' }))
        }))
      } catch (error) {
        if (!controller.signal.aborted) setError(errorMessage(error))
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [token, offset, cache])

  return (
    <section>
      <p className="eyebrow">TEAM MEMBER</p>
      <h1>Claim review</h1>
      {loading && <p role="status">Loading claims...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {!loading && !error && page && (
        <>
          {page.data.length === 0 && <p className="empty-state">No claims found.</p>}
          <div className="claim-list">
            {page.data.map(claim => (
              <button className="claim-row" type="button" key={claim.id} onClick={() => onSelect(claim.id)}>
                <strong>{names[claim.item_id] ?? 'Loading item...'}</strong>
                <span title={claim.claimant_id}>Claimant: {claim.claimant_id.slice(0, 8)}</span>
                <span>{dateTime(claim.created_at)}</span>
                <span className={`status-pill ${claim.status}`}>{claim.status}</span>
              </button>
            ))}
          </div>
          {(page.total > LIMIT || offset > 0) && (
            <div className="pagination">
              <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← Previous</button>
              <button type="button" disabled={offset + LIMIT >= page.total} onClick={() => setOffset(offset + LIMIT)}>Next →</button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function ClaimReview({ id, token, cache, onBack }: {
  id: string; token: string; cache: ItemCache; onBack: () => void
}) {
  const [claim, setClaim] = useState<ClaimDetail | null>(null)
  const [item, setItem] = useState<Item | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [itemError, setItemError] = useState('')
  const [location, setLocation] = useState('')
  const [readiness, setReadiness] = useState<Pickup['status']>('not_ready')

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const detail = await apiRequest<ClaimDetail>(`/claims/${id}`, token, { signal: controller.signal })
        if (controller.signal.aborted) return
        setClaim(detail)
        setLocation(detail.pickup?.location ?? '')
        setReadiness(detail.pickup?.status ?? 'not_ready')
        const result = await cachedItem(cache, detail.item_id, token)
        if (controller.signal.aborted) return
        setItem(result)
        if (!result) setItemError('Unable to load item information.')
      } catch (error) {
        if (!controller.signal.aborted) setError(errorMessage(error))
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [id, token, cache])

  async function decide(status: 'approved' | 'rejected') {
    if (busy || !claim || !window.confirm(`${status === 'approved' ? 'Approve' : 'Reject'} this claim?`)) return
    setBusy(true)
    setError('')
    try {
      await apiRequest(`/claims/${id}/decision`, token, { method: 'PATCH', body: JSON.stringify({ status }) })
      // Invalidate the item: approval also changes its recovery status.
      cache.delete(claim.item_id)
      const detail = await apiRequest<ClaimDetail>(`/claims/${id}`, token)
      setClaim(detail)
      setLocation(detail.pickup?.location ?? '')
      setReadiness(detail.pickup?.status ?? 'not_ready')
      const result = await cachedItem(cache, detail.item_id, token)
      setItem(result)
      setItemError(result ? '' : 'Unable to load item information.')
    } catch (error) {
      setError(error instanceof ApiError ? decisionMessages[error.code] ?? error.message : errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function savePickup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const trimmed = location.trim()
    if (!trimmed || trimmed.length > 200) {
      setError('Pickup location is required and must be at most 200 characters.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const pickup = await apiRequest<Pickup>(`/claims/${id}/pickup`, token, {
        method: 'PATCH', body: JSON.stringify({ location: trimmed, status: readiness }),
      })
      setClaim(previous => previous ? { ...previous, pickup } : previous)
      setLocation(pickup.location)
      setReadiness(pickup.status)
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  async function markReturned() {
    if (busy || !item || !window.confirm('Mark this item as returned?')) return
    setBusy(true)
    setError('')
    try {
      const updated = await apiRequest<Item>(`/items/${item.id}/status`, token, {
        method: 'PATCH', body: JSON.stringify({ status: 'returned' }),
      })
      setItem(updated)
      cache.set(updated.id, Promise.resolve(updated))
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="details-view">
      <button className="back-button" type="button" disabled={busy} onClick={onBack}>← Back to claims</button>
      <h1>Claim detail</h1>
      {loading && <p role="status">Loading claim...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {!loading && claim && (
        <div className="details-card">
          <h2>{item?.name ?? 'Unknown item'}</h2>
          {itemError && <p className="error-message" role="alert">{itemError}</p>}
          {item && <>
            <p><strong>Type:</strong> {item.type}</p>
            <p><strong>Item status:</strong> {item.status}</p>
            <p><strong>Location:</strong> {item.location}</p>
          </>}
          <p><strong>Claimant:</strong> {claim.claimant_id}</p>
          <h3>Ownership information</h3>
          <p className="ownership-information">{claim.ownership_information}</p>
          <p><strong>Claim status:</strong> <span className={`status-pill ${claim.status}`}>{claim.status}</span></p>
          <p><strong>Reviewed:</strong> {dateTime(claim.reviewed_at)}</p>
          <p><strong>Created:</strong> {dateTime(claim.created_at)}</p>
          {claim.status === 'pending' && (
            <div className="team-actions">
              <button className="hero-button" type="button" disabled={busy} onClick={() => void decide('approved')}>Approve</button>
              <button className="hero-button" type="button" disabled={busy} onClick={() => void decide('rejected')}>Reject</button>
            </div>
          )}
          {claim.status === 'approved' && (
            <>
              <h3>Campus pickup</h3>
              <form className="pickup-form" onSubmit={savePickup}>
                <label>Pickup location
                  <input value={location} required maxLength={200} disabled={busy} onChange={event => setLocation(event.target.value)} />
                </label>
                <label>Readiness
                  <select value={readiness} disabled={busy} onChange={event => setReadiness(event.target.value as Pickup['status'])}>
                    <option value="not_ready">Not ready</option>
                    <option value="ready">Ready</option>
                  </select>
                </label>
                <button className="hero-button" disabled={busy} type="submit">Save pickup</button>
              </form>
              {claim.pickup?.status === 'ready' && <p><strong>Ready at:</strong> {dateTime(claim.pickup.ready_at)}</p>}
              {item?.status === 'claimed' && <button className="hero-button" type="button" disabled={busy} onClick={() => void markReturned()}>Mark item returned</button>}
            </>
          )}
          {busy && <p role="status">Saving changes...</p>}
        </div>
      )}
    </section>
  )
}
