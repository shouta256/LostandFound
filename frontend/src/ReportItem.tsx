
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { AuthSession } from './GoogleLogin'
import { apiRequest } from './api'
import type { Item } from './api'

type ItemType = 'lost' | 'found'

const reportCopy = {
  lost: {
    eyebrow: 'REPORT A LOST ITEM',
    title: 'Report a lost item',
    intro: 'Tell us what you lost so the community can help you find it.',
    dateLabel: 'Date lost',
    locationLabel: 'Where did you lose it?',
    submit: 'Submit lost report →',
  },
  found: {
    eyebrow: 'REPORT A FOUND ITEM',
    title: 'Report a found item',
    intro: 'Tell us what you found so we can return it to its owner.',
    dateLabel: 'Date found',
    locationLabel: 'Where did you find it?',
    submit: 'Submit found report →',
  },
}

type Props = {
  session: AuthSession | null
  onCancel: () => void
  onSuccess: (notice?: string) => void
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
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoError, setPhotoError] = useState('')
  const [preview, setPreview] = useState('')
  const photoInput = useRef<HTMLInputElement>(null)
  const copy = reportCopy[type]

  useEffect(() => {
    if (preview) return () => URL.revokeObjectURL(preview)
  }, [preview])

  function choosePhoto(file: File | null) {
    setPhotoError('')
    setPhoto(null)
    setPreview('')
    if (file && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setPhotoError('Choose a JPEG, PNG or WebP photo.')
    } else if (file && file.size > 5 * 1024 * 1024) {
      setPhotoError('Photos must be at most 5 MiB.')
    } else {
      setPhoto(file)
      if (file) setPreview(URL.createObjectURL(file))
      return
    }
    if (photoInput.current) photoInput.current.value = ''
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading) return

    if (!session) {
      setError('Please sign in with Google before reporting an item.')
      return
    }

    if (!name.trim() || !description.trim() || !category.trim() || !location.trim()) {
      setError('Please fill in every field. Spaces alone are not enough.')
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
          category: category.trim(),
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

      if (photo) {
        try {
          const item: Item = await response.json()
          await apiRequest<Item>(`/items/${item.id}/photo`, session.access_token, {
            method: 'PUT', headers: { 'Content-Type': photo.type }, body: photo,
          })
        } catch {
          onSuccess('Your item was reported, but the photo could not be uploaded.')
          return
        }
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

      <p className="eyebrow">{copy.eyebrow}</p>
      <h1>{copy.title}</h1>
      <p className="report-intro">{copy.intro}</p>

      <form className={`report-form report-form-${type}`} onSubmit={handleSubmit}>
        <fieldset className="report-type-group">
          <legend>What would you like to report?</legend>

          <div className="report-type-toggle">
            <span className="report-type-thumb" aria-hidden="true" />
            <label>
              <input
                type="radio"
                name="item-type"
                value="lost"
                checked={type === 'lost'}
                onChange={() => setType('lost')}
              />
              <span>Lost item</span>
            </label>

            <label>
              <input
                type="radio"
                name="item-type"
                value="found"
                checked={type === 'found'}
                onChange={() => setType('found')}
              />
              <span>Found item</span>
            </label>
          </div>
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
            maxLength={80}
            required
          />
          <datalist id="item-categories">
            {categories.map((value) => (
              <option key={value} value={value} />
            ))}
          </datalist>
        </label>

        <label className="report-field">
          {copy.dateLabel}
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </label>

        <label className="report-field">
          {copy.locationLabel}
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Mabee Library"
            maxLength={200}
            required
          />
        </label>

        <label className="report-field">
          Photo (optional)
          <input
            ref={photoInput}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            disabled={loading}
            aria-describedby={photoError ? 'photo-error' : undefined}
            aria-invalid={!!photoError}
            onChange={(event) => choosePhoto(event.target.files?.[0] ?? null)}
          />
        </label>
        {photoError && <p id="photo-error" className="error-message" role="alert">{photoError}</p>}
        {photo && (
          <div className="report-photo">
            {preview && <img className="photo-preview" src={preview} alt="Selected item photo" />}
            <button type="button" className="report-cancel" disabled={loading} onClick={() => {
              choosePhoto(null)
              if (photoInput.current) photoInput.current.value = ''
            }}>Remove photo</button>
          </div>
        )}

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
            {loading ? 'Submitting...' : copy.submit}
          </button>
        </div>
      </form>
    </section>
  )
}
