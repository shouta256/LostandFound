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
}

function App() {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [page, setPage] = useState<ItemPage | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function loadItems() {
      try {
        const response = await fetch('/api/v1/items', { signal: controller.signal })
        if (!response.ok) throw new Error('Unable to load items. Please try again later.')
        setPage(await response.json())
      } catch (error) {
        if (!controller.signal.aborted) {
          setError(error instanceof Error ? error.message : 'Unable to load items.')
        }
      }
    }

    void loadItems()
    return () => controller.abort()
  }, [])

  return (
    <main>
      <h1>Lost &amp; Found Tracker</h1>
      <GoogleLogin session={session} onLogin={setSession} />

      {!page && !error && <p role="status">Loading items…</p>}
      {error && <p role="alert">{error}</p>}
      {page && (
        <>
          {page.data.length === 0 ? (
            <p>No items to display yet.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Type</th>
                    <th scope="col">Name</th>
                    <th scope="col">Description</th>
                    <th scope="col">Category</th>
                    <th scope="col">Date</th>
                    <th scope="col">Location</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {page.data.map((item) => (
                    <tr key={item.id}>
                      <td>{item.type}</td>
                      <td>{item.name}</td>
                      <td>{item.description}</td>
                      <td>{item.category}</td>
                      <td>{item.date}</td>
                      <td>{item.location}</td>
                      <td>{item.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </main>
  )
}

export default App
