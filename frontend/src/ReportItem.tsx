
import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AuthSession } from './GoogleLogin'

type ItemType = 'lost' | 'found'

type Props = {
  session: AuthSession | null
  onCancel: () => void
  onSuccess: () => void
}

const categories = [
  'Electronics',
  'Bags',
  'Accessories',
  'Clothing',
]

export default function ReportItem({
  session,
  onCancel,
  onSuccess,
}: Props) {
  const [type, setType] = useState<ItemType>('lost')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [date, setDate] = useState('')
  const [location, setLocation] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading) return

    if (!session) {
      setError('Please sign in with Google before reporting an item.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch('/api/v1/items', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          type,
          name: name.trim(),
          description: description.trim(),
          category,
          date,
          location: location.trim(),
        }),
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Your session has expired. Please sign in again.')
        }
        if (response.status === 422) {
          throw new Error('Please check your information and try again.')
        }
        throw new Error('Unable to report item. Please try again.')
      }

      onSuccess()
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Unable to report item.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="report-view">
      <button
        type="button"
        className="back-button"
        onClick={onCancel}
        disabled={loading}
      >
        ← Back to items
      </button>

      <p className="eyebrow">HELP YOUR CAMPUS COMMUNITY</p>
      <h1>Report an item</h1>
      <p className="report-intro">
        Lost something or found something on campus?
        Fill out the details below to help reconnect items
        with their owners.
      </p>

      <form className="report-form" onSubmit={handleSubmit}>
        <fieldset className="report-type-group">
          <legend>What would you like to report?</legend>

          <label>
            <input
              type="radio"
              name="item-type"
              value="lost"
              checked={type === 'lost'}
              onChange={() => setType('lost')}
            />
            Lost item
          </label>

          <label>
            <input
              type="radio"
              name="item-type"
              value="found"
              checked={type === 'found'}
              onChange={() => setType('found')}
            />
            Found item
          </label>
        </fieldset>

        <label className="report-field">
          Item name
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Black backpack"
            maxLength={120}
            required
          />
        </label>

        <label className="report-field">
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the item..."
            maxLength={2000}
            rows={5}
            required
          />
        </label>

        <label className="report-field">
          Category
          <input
            type="text"
            list="item-categories"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g. Electronics or School supplies"
            required
          />
          <datalist id="item-categories">
            {categories.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
        </label>

        <label className="report-field">
          Date lost or found
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </label>

        <label className="report-field">
          Location
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Mabee Library"
            maxLength={200}
            required
          />
        </label>

        {!session && (
          <p className="report-notice">
            Please sign in with Google to submit your report.
          </p>
        )}

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        <div className="report-actions">
          <button
            type="button"
            className="report-cancel"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>

          <button
            type="submit"
            className="hero-button"
            disabled={loading || !session}
          >
            {loading ? 'Submitting...' : 'Submit report →'}
          </button>
        </div>
      </form>
    </section>
  )
}
