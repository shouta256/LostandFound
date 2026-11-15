import { useEffect, useState } from 'react'
import { apiRequest, errorMessage } from './api'
import type { Claim, ClaimDetail, ClaimPage, Item } from './api'

const LIMIT = 20
const explanations: Record<Claim['status'], string> = {
  pending: 'Waiting for a team member to review your claim.',
  approved: 'Your claim was approved.',
  rejected: 'Your claim was not approved.',
}

function dateTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : 'Not reviewed'
}

export default function MyClaims({ token }: { token: string }) {
  const [claimId, setClaimId] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)

  return claimId ? (
    <MyClaimDetail key={claimId} id={claimId} token={token} onBack={() => setClaimId(null)} />
  ) : (
    <MyClaimList token={token} offset={offset} setOffset={setOffset} onSelect={setClaimId} />
  )
}

function MyClaimList({ token, offset, setOffset, onSelect }: {
  token: string
  offset: number
  setOffset: (offset: number) => void
  onSelect: (id: string) => void
}) {
  const [page, setPage] = useState<ClaimPage | null>(null)
  const [names, setNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    // Keep the cache within this load so aborted lookups are never reused.
    const cache = new Map<string, Promise<Item | null>>()
    async function load() {
      setLoading(true)
      setError('')
      setPage(null)
      setNames({})
      try {
        const result = await apiRequest<ClaimPage>(`/claims?limit=${LIMIT}&offset=${offset}`, token, { signal: controller.signal })
        if (controller.signal.aborted) return
        setPage(result)
        setLoading(false)
        await Promise.all(result.data.map(async claim => {
          let request = cache.get(claim.item_id)
          if (!request) {
            request = apiRequest<Item>(`/items/${claim.item_id}`, token, { signal: controller.signal }).catch(() => null)
            cache.set(claim.item_id, request)
          }
          const item = await request
          if (!controller.signal.aborted) {
            setNames(previous => ({ ...previous, [claim.item_id]: item?.name ?? 'Unknown item' }))
          }
        }))
      } catch (error) {
        if (!controller.signal.aborted) setError(errorMessage(error))
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [token, offset])

  return (
    <section className="my-claims-view">
      <p className="eyebrow">MY ACTIVITY</p>
      <h1>My claims</h1>
      {loading && <p role="status">Loading claims...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {!loading && !error && page && (
        <>
          {page.data.length === 0 && <p className="empty-state">You have not submitted any claims yet.</p>}
          <div className="claim-list">
            {page.data.map(claim => (
              <button className="claim-row" type="button" key={claim.id} onClick={() => onSelect(claim.id)}>
                <strong>{names[claim.item_id] ?? 'Loading item...'}</strong>
                <span>Submitted: {dateTime(claim.created_at)}</span>
                <span className={`status-pill ${claim.status}`}>{claim.status}</span>
              </button>
            ))}
          </div>
          {(page.total > LIMIT || offset > 0) && (
            <div className="pagination">
              <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← Previous</button>
              <span>Page {Math.floor(offset / LIMIT) + 1} of {Math.max(1, Math.ceil(page.total / LIMIT))}</span>
              <button type="button" disabled={offset + LIMIT >= page.total} onClick={() => setOffset(offset + LIMIT)}>Next →</button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function MyClaimDetail({ id, token, onBack }: { id: string; token: string; onBack: () => void }) {
  const [claim, setClaim] = useState<ClaimDetail | null>(null)
  const [item, setItem] = useState<Item | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [itemError, setItemError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setError('')
      setItemError('')
      setClaim(null)
      setItem(null)
      try {
        const detail = await apiRequest<ClaimDetail>(`/claims/${id}`, token, { signal: controller.signal })
        if (controller.signal.aborted) return
        setClaim(detail)
        // Refresh item status on every detail visit, including after pickup.
        try {
          const result = await apiRequest<Item>(`/items/${detail.item_id}`, token, { signal: controller.signal })
          if (!controller.signal.aborted) setItem(result)
        } catch {
          if (!controller.signal.aborted) setItemError('Unable to load item information.')
        }
      } catch (error) {
        if (!controller.signal.aborted) setError(errorMessage(error))
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [id, token])

  return (
    <section className="details-view my-claims-view">
      <button className="back-button" type="button" onClick={onBack}>← Back to my claims</button>
      <h1>Claim detail</h1>
      {loading && <p role="status">Loading claim...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {!loading && !error && claim && (
        <div className="details-card">
          <h2>{item?.name ?? 'Unknown item'}</h2>
          {itemError && <p className="error-message" role="alert">{itemError}</p>}
          {item?.photo_url && <img className="item-photo details-photo" src={item.photo_url} alt={item.name} />}
          <span className={`status-pill ${claim.status}`}>{claim.status}</span>
          <p>{explanations[claim.status]}</p>
          <p><strong>Submitted:</strong> {dateTime(claim.created_at)}</p>
          <p><strong>Reviewed:</strong> {dateTime(claim.reviewed_at)}</p>
          <h3>Ownership information</h3>
          <p className="ownership-information">{claim.ownership_information}</p>
          {claim.status === 'approved' && (
            <div className="pickup-box">
              <h3>Pickup</h3>
              {item?.status === 'returned' ? <p><strong>Returned</strong></p> : claim.pickup ? (
                <>
                  <p><strong>Location:</strong> {claim.pickup.location}</p>
                  <p>{claim.pickup.status === 'ready' ? 'Ready for pickup' : 'Not ready yet'}</p>
                  {claim.pickup.status === 'ready' && <p><strong>Ready at:</strong> {dateTime(claim.pickup.ready_at)}</p>}
                </>
              ) : <p>A team member will add pickup details soon.</p>}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
