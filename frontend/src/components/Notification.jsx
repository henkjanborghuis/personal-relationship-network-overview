import { useEffect, useState } from 'react'

/**
 * Centered modal overlay for loading, success, and error states.
 *
 * type='loading' — spinner + message, no dismiss, non-interactive backdrop
 * type='success' — green header, auto-dismisses after 5 s, backdrop click to dismiss
 * type='error'   — red header, stays until dismissed
 */
function formatElapsed(seconds) {
  const m = Math.floor(seconds / 60)
  const s = String(seconds % 60).padStart(2, '0')
  return `${m}:${s}`
}

export default function Notification({ type, title, details, onClose }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (type === 'loading') {
      setElapsed(0)
      const t = setInterval(() => setElapsed(s => s + 1), 1000)
      return () => clearInterval(t)
    }
  }, [type])

  useEffect(() => {
    if (type === 'success') {
      const t = setTimeout(onClose, 5000)
      return () => clearTimeout(t)
    }
  }, [type, onClose])

  const isLoading = type === 'loading'
  const isSuccess = type === 'success'

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      {/* Backdrop — not clickable during loading */}
      <div
        className="absolute inset-0 bg-black/20 dark:bg-black/40"
        onClick={isLoading ? undefined : onClose}
      />

      {/* Card */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-80 overflow-hidden">

        {isLoading ? (
          /* Loading state: spinner + message */
          <div className="px-6 py-6 flex flex-col items-center gap-4">
            <div className="w-8 h-8 rounded-full border-2 border-gray-200 dark:border-gray-600 border-t-blue-500 dark:border-t-blue-400 animate-spin" />
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 text-center">{title}</p>
            <p className="text-xs tabular-nums text-gray-400 dark:text-gray-500">{formatElapsed(elapsed)}</p>
          </div>
        ) : (
          <>
            {/* Colour bar + title */}
            <div className={`px-4 py-3 flex items-center justify-between ${
              isSuccess
                ? 'bg-green-50 dark:bg-green-900/30 border-b border-green-100 dark:border-green-800'
                : 'bg-red-50 dark:bg-red-900/30 border-b border-red-100 dark:border-red-800'
            }`}>
              <span className={`font-semibold text-sm ${
                isSuccess ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'
              }`}>
                {title}
              </span>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 leading-none ml-3 text-lg"
                aria-label="Dismiss"
              >
                ×
              </button>
            </div>

            {/* Details */}
            {details && (
              <div className="px-4 py-3">
                <p className="text-sm text-gray-600 dark:text-gray-400 break-all">{details}</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
