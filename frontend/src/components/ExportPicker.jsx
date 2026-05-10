/**
 * Destination picker shown before the export runs.
 * Offers "Save to Downloads" (immediate) and "Choose in iCloud Drive…" (folder picker).
 */
export default function ExportPicker({ destinations, onPickDownloads, onPickICloud, onCancel }) {
  const btnClass = 'w-full py-2 px-3 text-sm text-left bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors'

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 dark:bg-black/40"
        onClick={onCancel}
      />

      {/* Card */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 w-80 overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
          <h2 className="font-semibold text-sm text-gray-800 dark:text-gray-100">
            Where do you want to save?
          </h2>
        </div>

        {/* Destination options */}
        <div className="px-4 py-4 flex flex-col gap-2">
          {destinations.downloads && (
            <button onClick={onPickDownloads} className={btnClass}>
              <span className="font-medium">Save to Downloads</span>
              <span className="block text-xs text-gray-400 dark:text-gray-500 mt-0.5 truncate">
                ~/Downloads
              </span>
            </button>
          )}
          {destinations.icloud && (
            <button onClick={onPickICloud} className={btnClass}>
              <span className="font-medium">Choose in iCloud Drive…</span>
              <span className="block text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                Select a subfolder
              </span>
            </button>
          )}
        </div>

        {/* Cancel */}
        <div className="px-4 pb-4 flex justify-end">
          <button
            onClick={onCancel}
            className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
