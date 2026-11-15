import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'

type Props = {
  id: string
  value: string
  onChange: (value: string) => void
  options: string[]
  disabled?: boolean
}

export default function CategoryCombobox({ id, value, onChange, options, disabled }: Props) {
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(-1)
  const wrapper = useRef<HTMLDivElement>(null)
  const listId = useId()
  const query = value.toLowerCase()
  const filtered = !query || options.some((option) => option.toLowerCase() === query)
    ? options : options.filter((option) => option.toLowerCase().includes(query))
  const active = open && highlight >= 0 && highlight < filtered.length ? highlight : -1

  useEffect(() => {
    if (!open) return
    function handlePointerDown(event: PointerEvent) {
      if (event.target instanceof Node && !wrapper.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [open])

  useEffect(() => {
    if (active >= 0) document.getElementById(`${listId}-${active}`)?.scrollIntoView({ block: 'nearest' })
  }, [active, listId])

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      setOpen(true)
      const next = active < 0 ? (event.key === 'ArrowDown' ? 0 : filtered.length - 1)
        : (active + (event.key === 'ArrowDown' ? 1 : -1) + filtered.length) % filtered.length
      setHighlight(filtered.length ? next : -1)
    } else if (event.key === 'Enter' && active >= 0 && !event.nativeEvent.isComposing) {
      event.preventDefault()
      onChange(filtered[active])
      setOpen(false)
    } else if (event.key === 'Escape' || event.key === 'Tab') {
      if (event.key === 'Escape' && open) event.preventDefault()
      setOpen(false)
    }
  }

  return (
    <div className="category-combobox" ref={wrapper}>
      <input
        id={id} type="text" role="combobox" value={value} disabled={disabled}
        aria-expanded={open && !disabled} aria-controls={listId} aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        autoComplete="off" placeholder="e.g. Electronics or School supplies" required maxLength={80}
        onFocus={() => { setOpen(true); setHighlight(-1) }}
        onClick={() => setOpen(true)} onBlur={() => setOpen(false)} onKeyDown={handleKeyDown}
        onChange={(event) => { onChange(event.target.value); setOpen(true); setHighlight(-1) }}
      />
      <span className="category-chevron" aria-hidden="true">⌄</span>
      {open && !disabled && (
        <div className="report-popover category-options" id={listId} role="listbox" aria-label="Category suggestions">
          {filtered.map((option, index) => (
            <div
              key={option} id={`${listId}-${index}`} role="option" aria-selected={value === option}
              className={`category-option${active === index ? ' highlighted' : ''}`}
              onPointerDown={(event) => event.preventDefault()}
              onPointerMove={() => setHighlight(index)}
              onClick={() => { onChange(option); setOpen(false) }}
            >
              <span>{option}</span><span aria-hidden="true">{value === option ? '✓' : ''}</span>
            </div>
          ))}
          {!filtered.length && <p className="category-empty">No suggestions. You can use your own category.</p>}
        </div>
      )}
    </div>
  )
}
