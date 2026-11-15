import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

type Props = {
  id: string
  'aria-labelledby': string
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

function dateValue(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function parseDate(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function monthStart(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

export default function DatePicker({ id, 'aria-labelledby': labelledBy, value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false)
  const [today, setToday] = useState(() => dateValue(new Date()))
  const [focused, setFocused] = useState(today)
  const [month, setMonth] = useState(() => monthStart(new Date()))
  const wrapper = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const popupId = useId()
  const monthId = useId()
  const currentMonth = monthStart(parseDate(today))
  const start = new Date(month.getFullYear(), month.getMonth(), 1 - month.getDay())
  const days = Array.from({ length: 42 }, (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index))

  function close() {
    setOpen(false)
    trigger.current?.focus()
  }

  useEffect(() => {
    if (!open) return
    function handlePointerDown(event: PointerEvent) {
      if (event.target instanceof Node && !wrapper.current?.contains(event.target)) setOpen(false)
    }
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        setOpen(false)
        trigger.current?.focus()
      }
    }
    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  useEffect(() => {
    if (open) wrapper.current?.querySelector<HTMLButtonElement>(`[data-date="${focused}"]`)?.focus()
  }, [open, focused, month])

  function select(day: string) {
    onChange(day)
    close()
  }

  function moveMonth(offset: number) {
    const next = new Date(month.getFullYear(), month.getMonth() + offset, 1)
    const day = Math.min(parseDate(focused).getDate(), new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate())
    const nextValue = dateValue(new Date(next.getFullYear(), next.getMonth(), day))
    setFocused(nextValue > today ? today : nextValue)
    setMonth(next)
  }

  function handleDayKey(event: KeyboardEvent<HTMLButtonElement>, day: Date) {
    const offset = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key]
    if (offset === undefined) return
    event.preventDefault()
    const next = new Date(day.getFullYear(), day.getMonth(), day.getDate() + offset)
    if (dateValue(next) > today) return
    setFocused(dateValue(next))
    setMonth(monthStart(next))
  }

  return (
    <div className="date-picker" ref={wrapper} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false)
    }}>
      <button
        type="button" className="date-trigger" id={id} ref={trigger} disabled={disabled}
        aria-labelledby={`${labelledBy} ${id}-value`} aria-haspopup="dialog" aria-expanded={open && !disabled} aria-controls={popupId}
        onClick={() => {
          const currentDay = dateValue(new Date())
          setToday(currentDay)
          const initial = value && value <= currentDay ? value : currentDay
          setFocused(initial)
          setMonth(monthStart(parseDate(initial)))
          setOpen(!open)
        }}
      >
        <span id={`${id}-value`} className={value ? undefined : 'date-placeholder'}>
          {value ? parseDate(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Select a date'}
        </span>
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <rect x="3" y="5" width="18" height="16" rx="3" /><path d="M7 3v4m10-4v4M3 11h18" />
        </svg>
      </button>
      {open && !disabled && (
        <div className="report-popover calendar" id={popupId} role="dialog" aria-label="Choose a report date" tabIndex={-1}>
          <div className="calendar-header">
            <button type="button" aria-label="Previous month" onClick={() => moveMonth(-1)}>‹</button>
            <span id={monthId} aria-live="polite">{month.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</span>
            <button type="button" aria-label="Next month" disabled={month >= currentMonth} onClick={() => moveMonth(1)}>›</button>
          </div>
          <div role="grid" aria-labelledby={monthId}>
            <div className="calendar-week" role="row">
              {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((day) => <span key={day} role="columnheader">{day}</span>)}
            </div>
            {Array.from({ length: 6 }, (_, week) => (
              <div className="calendar-week" role="row" key={week}>
                {days.slice(week * 7, week * 7 + 7).map((day) => {
                  const key = dateValue(day)
                  return (
                    <div role="gridcell" aria-selected={key === value} key={key}>
                      <button
                        type="button" data-date={key} tabIndex={key === focused ? 0 : -1} disabled={key > today}
                        className={`calendar-day${day.getMonth() !== month.getMonth() ? ' other-month' : ''}${key === today ? ' today' : ''}`}
                        aria-label={day.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                        aria-pressed={key === value} aria-current={key === today ? 'date' : undefined}
                        onFocus={() => setFocused(key)} onKeyDown={(event) => handleDayKey(event, day)} onClick={() => select(key)}
                      >{day.getDate()}</button>
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
          <div className="calendar-footer">
            <button type="button" onClick={() => select(today)}>Today</button>
            <button type="button" onClick={() => select('')}>Clear</button>
          </div>
        </div>
      )}
    </div>
  )
}
