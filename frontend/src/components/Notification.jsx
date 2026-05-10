import { useEffect } from 'react'

/**
 * Centered modal notification overlay.
 * Success notifications auto-dismiss after 5 s.
 */
export default function Notification({ type, title, details, onClose }) {
  useEffect(() => {
    if (type === 'success') {
      const t = setTimeout(onClose, 5000)
      return () => clearTimeout(t)
    }
  }, [type, onClose])

  const isSuccess = type === 'success'

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 dark:bg-black/40"
        onClick={onClose}
      />

      {/* Card */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-80 overflow-hidden">
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
      </div>
    </div>
  )
}
