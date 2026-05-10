export default function GroupSidebar({ groups, selectedGroup, onSelectGroup, onSync, syncing, onExport, exporting, isStatic, collapsed, onToggleCollapse, isDark, onToggleDark }) {
  return (
    <aside
      className={[
        'shrink-0 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full transition-all duration-200',
        collapsed ? 'w-10' : 'w-56',
      ].join(' ')}
    >
      {/* Header row — collapse toggle only */}
      <div className="flex items-center justify-end px-3 py-4 border-b border-gray-200 dark:border-gray-700 min-h-[53px]">
        <button
          onClick={onToggleCollapse}
          className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-lg leading-none shrink-0"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      {/* Nav — hidden when collapsed */}
      {!collapsed && (
        <nav className="flex-1 min-h-0 overflow-y-auto py-2">
          {/* My Contacts section heading */}
          <div className="px-4 pb-1 pt-1">
            <p className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">My Contacts</p>
          </div>

          <button
            onClick={() => onSelectGroup(null)}
            className={`w-full text-left px-4 py-2 text-sm flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
              selectedGroup === null
                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium'
                : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            <span>All contacts</span>
          </button>

          {groups.length > 0 && (
            <div className="mt-2 px-4 pb-1">
              <p className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">Groups</p>
            </div>
          )}

          {groups.map(g => (
            <button
              key={g.name}
              onClick={() => onSelectGroup(g.name)}
              className={`w-full text-left px-4 py-2 text-sm flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors ${
                selectedGroup === g.name
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium'
                  : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              <span className="truncate">{g.name}</span>
              <span className="ml-2 text-xs text-gray-400 dark:text-gray-500 shrink-0">{g.count}</span>
            </button>
          ))}
        </nav>
      )}

      {/* Bottom controls */}
      <div className={collapsed ? 'flex flex-col items-center py-3 gap-3 border-t border-gray-200 dark:border-gray-700' : 'flex flex-col border-t border-gray-200 dark:border-gray-700'}>

        {/* Sync + Export actions */}
        {!isStatic && !collapsed && (
          <div className="px-4 pt-4 pb-3 flex flex-col gap-2">
            <button
              onClick={onSync}
              disabled={syncing}
              className="w-full py-2 px-3 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300 transition-colors"
            >
              {syncing ? 'Syncing…' : 'Sync Contacts'}
            </button>
            <button
              onClick={onExport}
              disabled={exporting}
              className="w-full py-2 px-3 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300 transition-colors"
            >
              {exporting ? 'Exporting…' : 'Export to HTML'}
            </button>
          </div>
        )}

        {/* Dark mode toggle — separated by a top border when expanded */}
        {collapsed ? (
          <button
            onClick={onToggleDark}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-lg leading-none"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? '☀' : '☾'}
          </button>
        ) : (
          <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {isDark ? 'Dark mode' : 'Light mode'}
            </span>
            <button
              onClick={onToggleDark}
              className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-lg leading-none"
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? '☀' : '☾'}
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
