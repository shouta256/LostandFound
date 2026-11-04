import { useEffect, useId, useRef, useState } from 'react'
import type { AuthSession } from './GoogleLogin'

type Props = {
  user: AuthSession['user']
  onSignOut: () => void
}

function ProfileMenu({ user, onSignOut }: Props) {
  const [open, setOpen] = useState(false)
  const menu = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const popupId = useId()
  const name = user.name?.trim()
  const initials = (name
    ? name.split(/\s+/).slice(0, 2).map((word) => word[0]).join('')
    : user.email[0]
  ).toUpperCase()

  useEffect(() => {
    if (!open) return

    function handlePointerDown(event: PointerEvent) {
      if (event.target instanceof Node && !menu.current?.contains(event.target)) {
        setOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
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

  function handleSignOut() {
    window.google?.accounts.id.disableAutoSelect()
    setOpen(false)
    onSignOut()
  }

  return (
    <div className="profile-menu" ref={menu}>
      <button
        type="button"
        className="profile-avatar"
        ref={trigger}
        aria-label="Account menu"
        aria-expanded={open}
        aria-controls={popupId}
        onClick={() => setOpen((previous) => !previous)}
      >
        {initials}
      </button>

      {open && (
        <div className="profile-popup" id={popupId}>
          <div className="profile-details">
            <strong>{name || user.email}</strong>
            {name && <p>{user.email}</p>}
          </div>
          <button
            type="button"
            className="profile-sign-out"
            onClick={handleSignOut}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

export default ProfileMenu
