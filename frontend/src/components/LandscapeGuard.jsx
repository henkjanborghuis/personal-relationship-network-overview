import { useEffect, useState } from 'react'

/**
 * On narrow/mobile screens, shows a "rotate device" overlay when portrait.
 * On tablets and desktops the overlay is never shown.
 */
export default function LandscapeGuard({ children }) {
  const [showOverlay, setShowOverlay] = useState(false)

  useEffect(() => {
    const check = () => {
      // Only enforce on devices where landscape matters (narrow or short screens)
      const isMobile = window.innerWidth < 1024 || window.innerHeight < 600
      const isPortrait = window.matchMedia('(orientation: portrait)').matches
      setShowOverlay(isMobile && isPortrait)
    }
    check()
    window.addEventListener('resize', check)
    window.addEventListener('orientationchange', check)
    return () => {
      window.removeEventListener('resize', check)
      window.removeEventListener('orientationchange', check)
    }
  }, [])

  return (
    <>
      {children}
      {showOverlay && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-gray-950/95 text-white select-none">
          <div className="text-6xl mb-6 animate-pulse">↻</div>
          <p className="text-lg font-semibold">Rotate your device</p>
          <p className="text-sm text-gray-400 mt-2">This app works best in landscape mode</p>
        </div>
      )}
    </>
  )
}
