import { useEffect, useState } from 'react'
import type { AuthSession } from './GoogleLogin'
import ProfileMenu from './ProfileMenu'
import { apiRequest, errorMessage } from './api'
import type { Item } from './api'
import TeamClaims from './TeamClaims'
import ReportItem from './ReportItem'

type ItemPage = {
  data: Item[]
  total: number
  limit: number
  offset: number
}

type Filter = 'all' | 'lost' | 'found'

const LIMIT = 20

const categories = [
  'Electronics',
  'Bags',
  'Accessories',
  'Clothing',
]

type Props = {
  session: AuthSession
  onSignOut: () => void
}

function ItemBrowser({ session, onSignOut }: Props) {
  const [view, setView] = useState<'items' | 'claims' | 'report'>('items')
  const [returnBusy, setReturnBusy] = useState(false)
  const [returnError, setReturnError] = useState('')
  const isTeamMember = session.user.role === 'team_member'
  const [page, setPage] = useState<ItemPage | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshKey, setRefreshKey] = useState(0)

  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [category, setCategory] = useState('')
  const [offset, setOffset] = useState(0)

  const [selectedItem, setSelectedItem] = useState<Item | null>(null)

  // Wait briefly before sending search requests.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim())
    }, 300)

    return () => window.clearTimeout(timer)
  }, [search])

  // Fetch items from the backend using server-side filters.
  useEffect(() => {
    if (view !== 'items') return
    const controller = new AbortController()

    async function loadItems() {
      setLoading(true)
      setError('')
      setPage(null)

      const params = new URLSearchParams()

      if (debouncedSearch) {
        params.set('q', debouncedSearch)
      }

      if (filter !== 'all') {
        params.set('type', filter)
      }

      if (category) {
        params.set('category', category)
      }

      params.set('limit', String(LIMIT))
      params.set('offset', String(offset))

      try {
        const response = await fetch(
          `/api/v1/items?${params.toString()}`,
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(
            'Unable to load items. Please try again later.'
          )
        }

        const result: ItemPage = await response.json()

        if (!controller.signal.aborted) {
          setPage(result)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Unable to load items.'
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadItems()

    return () => controller.abort()
  }, [debouncedSearch, filter, category, offset, view, refreshKey])

  function changeFilter(next: Filter) {
    setView('items')
    setReturnError('')
    setFilter(next)
    setOffset(0)
    setSelectedItem(null)
  }

  function changeCategory(next: string) {
    setView('items')
    setReturnError('')
    setCategory(next)
    setOffset(0)
    setSelectedItem(null)
  }

  function changeSearch(next: string) {
    setView('items')
    setReturnError('')
    setSearch(next)
    setOffset(0)
    setSelectedItem(null)
  }

  async function markReturned() {
    if (returnBusy || !selectedItem || !window.confirm('Mark this item as returned?')) return
    setReturnBusy(true)
    setReturnError('')
    try {
      const updated = await apiRequest<Item>(`/items/${selectedItem.id}/status`, session.access_token, {
        method: 'PATCH', body: JSON.stringify({ status: 'returned' }),
      })
      setSelectedItem(current => current?.id === updated.id ? updated : current)
      setPage(current => current ? {
        ...current,
        data: current.data.filter(item => item.id !== updated.id),
        total: Math.max(0, current.total - (current.data.some(item => item.id === updated.id) ? 1 : 0)),
      } : current)
    } catch (error) {
      setReturnError(errorMessage(error))
    } finally {
      setReturnBusy(false)
    }
  }

  function handleReport() {
    setSelectedItem(null)
    setView('report')
}

  const total = page?.total ?? 0
  const currentPage = Math.floor(offset / LIMIT) + 1
  const totalPages = Math.ceil(total / LIMIT)

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">⌕</span>
          <span>Lost &amp; Found</span>
        </div>

        <p className="campus-label">WASHBURN CAMPUS</p>

        <div className="sidebar-section">
          <p className="sidebar-heading">FIND AN ITEM</p>

          <input
            className="search-input"
            type="search"
            placeholder="Search by keyword..."
            aria-label="Search items"
            value={search}
            maxLength={200}
            onChange={(e) => changeSearch(e.target.value)}
          />
        </div>

        <div className="sidebar-section">
          <p className="sidebar-heading">BROWSE BY</p>

          <nav className="sidebar-nav" aria-label="Item filters">
            <button
              type="button"
              className={view === 'items' && filter === 'all' ? 'active' : ''}
              onClick={() => changeFilter('all')}
            >
              All items
            </button>

            <button
              type="button"
              className={view === 'items' && filter === 'lost' ? 'active' : ''}
              onClick={() => changeFilter('lost')}
            >
              Lost items
            </button>

            <button
              type="button"
              className={view === 'items' && filter === 'found' ? 'active' : ''}
              onClick={() => changeFilter('found')}
            >
              Found items
            </button>
          </nav>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-heading">CATEGORIES</p>

          <nav className="sidebar-nav" aria-label="Categories">
            {categories.map((name) => (
              <button
                key={name}
                type="button"
                className={view === 'items' && category === name ? 'active' : ''}
                onClick={() =>
                  changeCategory(category === name ? '' : name)
                }
              >
                {name}
              </button>
            ))}
          </nav>
        </div>

        {isTeamMember && (
          <div className="sidebar-section">
            <p className="sidebar-heading">TEAM MEMBER</p>
            <nav className="sidebar-nav" aria-label="Team member tools">
              <button type="button" className={view === 'claims' ? 'active' : ''}
                onClick={() => { setSelectedItem(null); setReturnError(''); setView('claims') }}>
                Claim review
              </button>
            </nav>
          </div>
        )}

        <button
          type="button"
          className="report-button"
          onClick={handleReport}
        >
          + Report lost or found
        </button>
      </aside>

      <div className="content-area">
        <header className="topbar">
          <div className="topbar-right">
            <span>Washburn University</span>
            <ProfileMenu user={session.user} onSignOut={onSignOut} />
          </div>
        </header>

        <main className="main-content">
          {view === 'report' ? (
            <ReportItem
              session={session}
              onCancel={() => setView('items')}
              onSuccess={() => {
                setView('items')
                setOffset(0)
                setRefreshKey((key) => key + 1)
}}
            />
          ) : view === 'claims' && isTeamMember ? (
            <TeamClaims token={session.access_token} />
          ) : selectedItem ? (
            <section className="details-view">
              <button
                type="button"
                className="back-button"
                onClick={() => setSelectedItem(null)}
              >
                ← Back to items
              </button>

              <p className="eyebrow">ITEM DETAILS</p>
              <h1>{selectedItem.name}</h1>

              <div className="details-card">
                <span className={`status-pill ${selectedItem.type}`}>
                  {selectedItem.type.toUpperCase()}
                </span>

                <p>
                  <strong>Category:</strong>{' '}
                  {selectedItem.category}
                </p>

                <p>
                  <strong>Location:</strong>{' '}
                  {selectedItem.location}
                </p>

                <p>
                  <strong>Date:</strong>{' '}
                  {selectedItem.date}
                </p>

                <p>
                  <strong>Status:</strong>{' '}
                  {selectedItem.status}
                </p>

                <h3>Description</h3>
                <p>{selectedItem.description}</p>
                {isTeamMember && (
                  <>
                    {((selectedItem.type === 'lost' && selectedItem.status === 'available') ||
                      (selectedItem.type === 'found' && selectedItem.status === 'claimed')) && (
                      <button className="hero-button" type="button" disabled={returnBusy} onClick={() => void markReturned()}>
                        {returnBusy ? 'Saving...' : 'Mark as returned'}
                      </button>
                    )}
                    {returnError && <p className="error-message" role="alert">{returnError}</p>}
                  </>
                )}
              </div>
            </section>
          ) : (
            <>
              <section className="hero">
                <p className="eyebrow">
                  YOUR CAMPUS. YOUR COMMUNITY.
                </p>

                <h1>
                  Good things find<br />
                  their way back.
                </h1>

                <p className="hero-description">
                  Lost something? Found something?
                  Help reunite people with their belongings.
                </p>

                <button
                  type="button"
                  className="hero-button"
                  onClick={handleReport}
                >
                  Report an item →
                </button>
              </section>

              <section className="items-section">
                <div className="section-header">
                  <div>
                    <p className="eyebrow">
                      EXPLORE THE COLLECTION
                    </p>

                    <h2>
                      {filter === 'all'
                        ? 'Recently reported'
                        : filter === 'lost'
                          ? 'Lost items'
                          : 'Found items'}
                    </h2>
                  </div>

                  {!loading && !error && page && (
                    <span className="item-count">
                      {page.total} items
                    </span>
                  )}
                </div>

                {loading && (
                  <p role="status">Loading items...</p>
                )}

                {error && (
                  <div
                    className="error-message"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                {!loading &&
                  !error &&
                  page &&
                  page.data.length === 0 && (
                    <div className="empty-state">
                      <h3>No items found</h3>
                      <p>
                        Try another keyword or change your filters.
                      </p>
                    </div>
                  )}

                {!loading &&
                  !error &&
                  page &&
                  page.data.length > 0 && (
                    <div className="item-grid">
                      {page.data.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className="item-card"
                          onClick={() => { setReturnError(''); setSelectedItem(item) }}
                        >
                          <div className="item-image-placeholder">
                            <span>⌕</span>
                          </div>

                          <div className="item-card-body">
                            <span
                              className={`status-pill ${item.type}`}
                            >
                              {item.type.toUpperCase()}
                            </span>

                            <h3>{item.name}</h3>
                            <p>{item.location}</p>

                            <p className="item-date">
                              {item.date}
                            </p>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}

                {!loading &&
                  !error &&
                  page &&
                  totalPages > 1 && (
                    <div className="pagination">
                      <button
                        type="button"
                        disabled={offset === 0}
                        onClick={() =>
                          setOffset(Math.max(0, offset - LIMIT))
                        }
                      >
                        ← Previous
                      </button>

                      <span>
                        Page {currentPage} of {totalPages}
                      </span>

                      <button
                        type="button"
                        disabled={offset + LIMIT >= total}
                        onClick={() =>
                          setOffset(offset + LIMIT)
                        }
                      >
                        Next →
                      </button>
                    </div>
                  )}
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  )
}

export default ItemBrowser
