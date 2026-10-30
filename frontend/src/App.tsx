
import { useEffect, useMemo, useState } from 'react'
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
}

type Filter = 'all' | 'lost' | 'found'

const categories = [
  'Electronics',
  'Bags & wallets',
  'Keys & accessories',
  'Other items',
]

function App() {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [page, setPage] = useState<ItemPage | null>(null)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [category, setCategory] = useState('')
  const [selectedItem, setSelectedItem] = useState<Item | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadItems() {
      try {
        const response = await fetch('/api/v1/items', {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error('Unable to load items. Please try again later.')
        }

        const result: ItemPage = await response.json()
        setPage(result)
        setError('')
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : 'Unable to load items.'
          )
        }
      }
    }

    void loadItems()
    return () => controller.abort()
  }, [])

  const filteredItems = useMemo(() => {
    const items = page?.data ?? []
    const query = search.trim().toLowerCase()

    return items.filter((item) => {
      const matchesType = filter === 'all' || item.type === filter

      const matchesCategory =
        !category || item.category.toLowerCase() === category.toLowerCase()

      const searchableText = [
        item.name,
        item.description,
        item.category,
        item.location,
      ].join(' ').toLowerCase()

      return (
        matchesType &&
        matchesCategory &&
        searchableText.includes(query)
      )
    })
  }, [page, search, filter, category])

  function changeFilter(next: Filter) {
    setFilter(next)
    setSelectedItem(null)
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">⌕</span>
          <span>findback.</span>
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
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="sidebar-section">
          <p className="sidebar-heading">BROWSE BY</p>
          <nav className="sidebar-nav" aria-label="Item filters">
            <button
              className={filter === 'all' ? 'active' : ''}
              onClick={() => changeFilter('all')}
            >
              All items
            </button>
            <button
              className={filter === 'lost' ? 'active' : ''}
              onClick={() => changeFilter('lost')}
            >
              Lost items
            </button>
            <button
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
                className={category === name ? 'active' : ''}
                onClick={() =>
                  setCategory(category === name ? '' : name)
                }
              >
                {name}
              </button>
            ))}
          </nav>
        </div>

        <button
          className="report-button"
          onClick={() => {
            window.alert('Report Item page is coming soon.')
          }}
        >
          + Report lost or found
        </button>
      </aside>

      <div className="content-area">
        <header className="topbar">
          <span>CAMPUS LOST & FOUND</span>
          <div className="topbar-right">
            <span>Washburn University</span>
            <GoogleLogin session={session} onLogin={setSession} />
          </div>
        </header>

        <main className="main-content">
          {selectedItem ? (
            <section className="details-view">
              <button
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

                <p><strong>Category:</strong> {selectedItem.category}</p>
                <p><strong>Location:</strong> {selectedItem.location}</p>
                <p><strong>Date:</strong> {selectedItem.date}</p>
                <p><strong>Status:</strong> {selectedItem.status}</p>

                <h3>Description</h3>
                <p>{selectedItem.description}</p>
              </div>
            </section>
          ) : (
            <>
              <section className="hero">
                <p className="eyebrow">YOUR CAMPUS. YOUR COMMUNITY.</p>
                <h1>Good things find<br />their way back.</h1>
                <p className="hero-description">
                  Lost something? Found something?
                  Help reunite people with their belongings.
                </p>
                <button
                  className="hero-button"
                  onClick={() =>
                    window.alert('Report Item page is coming soon.')
                  }
                >
                  Report an item →
                </button>
              </section>

              <section className="items-section">
                <div className="section-header">
                  <div>
                    <p className="eyebrow">EXPLORE THE COLLECTION</p>
                    <h2>
                      {filter === 'all'
                        ? 'Recently reported'
                        : filter === 'lost'
                          ? 'Lost items'
                          : 'Found items'}
                    </h2>
                  </div>
                  {page && (
                    <span className="item-count">
                      {filteredItems.length} items
                    </span>
                  )}
                </div>

                {!page && !error && (
                  <p role="status">Loading items...</p>
                )}

                {error && (
                  <div className="error-message" role="alert">
                    {error}
                  </div>
                )}

                {page && filteredItems.length === 0 && (
                  <div className="empty-state">
                    <h3>No items found</h3>
                    <p>Try another keyword or change your filters.</p>
                  </div>
                )}

                {page && filteredItems.length > 0 && (
                  <div className="item-grid">
                    {filteredItems.map((item) => (
                      <button
                        key={item.id}
                        className="item-card"
                        onClick={() => setSelectedItem(item)}
                      >
                        <div className="item-image-placeholder">
                          <span>⌕</span>
                        </div>
                        <div className="item-card-body">
                          <span className={`status-pill ${item.type}`}>
                            {item.type.toUpperCase()}
                          </span>
                          <h3>{item.name}</h3>
                          <p>{item.location}</p>
                          <p className="item-date">{item.date}</p>
                        </div>
                      </button>
                    ))}
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
