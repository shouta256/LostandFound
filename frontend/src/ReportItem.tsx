
import { useEffect, useRef, useState } from 'react'
import type { DragEvent, FormEvent } from 'react'
import CategoryCombobox from './CategoryCombobox'
import DatePicker from './DatePicker'
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
  const dragDepth = useRef(0)
  const [dragging, setDragging] = useState(false)
  const copy = reportCopy[type]

  useEffect(() => {
    if (preview) return () => URL.revokeObjectURL(preview)
  }, [preview])

  function choosePhoto(file: File | null) {
    if (loading) return
    if (photoInput.current) photoInput.current.value = ''
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
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (loading) return

    if (!session) {
      setError('Please sign in with Google before reporting an item.')
      return
    }

    if (!name.trim() || !description.trim() || !category.trim() || !date || !location.trim()) {
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

        <div className="report-field">
          <label htmlFor="report-category">Category</label>
          <CategoryCombobox id="report-category" value={category} onChange={setCategory} options={categories} disabled={loading} />
        </div>

        <div className="report-field">
          <label id="report-date-label" htmlFor="report-date">{copy.dateLabel}</label>
          <DatePicker id="report-date" aria-labelledby="report-date-label" value={date} onChange={setDate} disabled={loading} />
        </div>

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

        <div className="report-field">
          <span id="report-photo-label">Photo (optional)</span>
          <div
            className={`photo-dropzone${dragging && !loading ? ' dragging' : ''}`}
            aria-busy={loading}
            onDragEnter={(event) => {
              event.preventDefault()
              dragDepth.current += 1
              if (!loading) setDragging(true)
            }}
            onDragOver={(event: DragEvent<HTMLDivElement>) => {
              event.preventDefault()
              event.dataTransfer.dropEffect = loading ? 'none' : 'copy'
            }}
            onDragLeave={(event) => {
              event.preventDefault()
              dragDepth.current = Math.max(0, dragDepth.current - 1)
              if (!dragDepth.current) setDragging(false)
            }}
            onDrop={(event) => {
              event.preventDefault()
              dragDepth.current = 0
              setDragging(false)
              if (!loading && event.dataTransfer.files.length) choosePhoto(event.dataTransfer.files[0])
            }}
          >
            <input
              className="photo-input" ref={photoInput} id="report-photo" type="file"
              accept="image/jpeg,image/png,image/webp" disabled={loading} tabIndex={-1}
              aria-labelledby="report-photo-label" aria-describedby={photoError ? 'photo-hint photo-error' : 'photo-hint'}
              aria-invalid={!!photoError}
              onChange={(event) => choosePhoto(event.target.files?.[0] ?? null)}
            />
            {photo ? (
              <div className="photo-selection">
                {preview && <img className="photo-preview" src={preview} alt="Selected item photo" />}
                <div className="photo-information">
                  <span className="photo-name">{photo.name}</span>
                  <span className="photo-size">{photo.size < 1024 * 1024 ? `${Math.max(1, Math.round(photo.size / 1024))} KB` : `${(photo.size / (1024 * 1024)).toFixed(1)} MB`}</span>
                  <div className="photo-actions">
                    <button type="button" disabled={loading} aria-describedby={photoError ? 'photo-error' : undefined} onClick={() => photoInput.current?.click()}>Replace</button>
                    <button type="button" disabled={loading} onClick={() => choosePhoto(null)}>Remove</button>
                  </div>
                </div>
              </div>
            ) : (
              <button
                type="button" className="photo-browse" disabled={loading}
                aria-labelledby="report-photo-label photo-prompt" aria-describedby={photoError ? 'photo-hint photo-error' : 'photo-hint'}
                onClick={() => photoInput.current?.click()}
              >
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                  <rect x="3" y="3" width="18" height="18" rx="4" /><circle cx="8" cy="8" r="1.5" /><path d="m3 17 5-5 4 4 4-6 5 7" />
                </svg>
                <span id="photo-prompt">Drag &amp; drop a photo here <span className="photo-browse-line">or <strong>browse</strong></span></span>
              </button>
            )}
            <span className="photo-hint" id="photo-hint">JPEG, PNG or WebP · up to 5 MiB</span>
          </div>
          {photoError && <p id="photo-error" className="error-message" role="alert">{photoError}</p>}
        </div>

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
