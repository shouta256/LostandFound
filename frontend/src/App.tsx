import ReportItem from './ReportItem'
import { useEffect, useState } from 'react'
import GoogleLogin from './GoogleLogin'
import type { AuthSession } from './GoogleLogin'
import './App.css'

type Item = {
  id: string
  type: 'lost' | 'found'
  name: string
  description: string
  category: string
  date: string
  location: string
  status: 'available' | 'claimed' | 'returned'
}

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

function App() {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [page, setPage] = useState<ItemPage | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [category, setCategory] = useState('')
  const [offset, setOffset] = useState(0)

  const [selectedItem, setSelectedItem] = useState<Item | null>(null)

  const [showReportForm, setShowReportForm] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  function handleReportSuccess() {
    setShowReportForm(false)
    setSelectedItem(null)
    setSearch('')
    setDebouncedSearch('')
    setFilter('all')
    setCategory('')
    setOffset(0)
    setRefreshKey((value) => value + 1)
  }

  // Wait briefly before sending search requests.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim())
    }, 300)

    return () => window.clearTimeout(timer)
  }, [search])

  // Fetch items from the backend using server-side filters.
  useEffect(() => {
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
  }, [debouncedSearch, filter, category, offset, refreshKey])

  function changeFilter(next: Filter) {
    setFilter(next)
    setOffset(0)
    setSelectedItem(null)
  }

  function changeCategory(next: string) {
    setCategory(next)
    setOffset(0)
    setSelectedItem(null)
  }

  function changeSearch(next: string) {
    setSearch(next)
    setOffset(0)
    setSelectedItem(null)
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
              className={filter === 'all' ? 'active' : ''}
              onClick={() => changeFilter('all')}
            >
              All items
            </button>

            <button
              type="button"
              className={filter === 'lost' ? 'active' : ''}
              onClick={() => changeFilter('lost')}
            >
              Lost items
            </button>

            <button
              type="button"
              className={filter === 'found' ? 'active' : ''}
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
                className={category === name ? 'active' : ''}
                onClick={() =>
                  changeCategory(category === name ? '' : name)
                }
              >
                {name}
              </button>
            ))}
          </nav>
        </div>

        <button
          type="button"
          className="report-button"
          onClick={() => {
            setSelectedItem(null)
            setShowReportForm(true)
          }}
        >
          + Report lost or found
        </button>
      </aside>

      <div className="content-area">
        <header className="topbar">
          <div className="topbar-right">
            <span>Washburn University</span>
            <GoogleLogin
              session={session}
              onLogin={setSession}
            />
          </div>
        </header>

        <main className="main-content">
          {showReportForm ? (
            <ReportItem
             session={session}
             onCancel={() => setShowReportForm(false)}
            onSuccess={handleReportSuccess}
          />
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
                  onClick={() => {
                    setSelectedItem(null)
                    setShowReportForm(true)
                  }}

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
                          onClick={() => setSelectedItem(item)}
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

export default App
