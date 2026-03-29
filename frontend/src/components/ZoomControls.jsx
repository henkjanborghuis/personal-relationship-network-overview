/**
 * Floating zoom controls overlay — shown over the family tree panel.
 */
export default function ZoomControls({ zoom, onZoomIn, onZoomOut, onFit }) {
  return (
    <div className="absolute bottom-4 right-4 z-10 flex items-center gap-0.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-md px-1 py-1">
      <button
        onClick={onZoomOut}
        className="w-7 h-7 flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-base font-medium transition-colors"
        title="Zoom out"
      >
        −
      </button>
      <button
        onClick={onFit}
        className="px-2 h-7 flex items-center text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors font-mono tabular-nums min-w-[44px] justify-center"
        title="Fit to screen"
      >
        {Math.round(zoom * 100)}%
      </button>
      <button
        onClick={onZoomIn}
        className="w-7 h-7 flex items-center justify-center text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-base font-medium transition-colors"
        title="Zoom in"
      >
        +
      </button>
    </div>
  )
}
