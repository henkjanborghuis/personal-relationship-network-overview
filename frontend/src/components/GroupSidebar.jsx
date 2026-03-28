export default function GroupSidebar({ groups, selectedGroup, onSelectGroup, onSync, syncing, isStatic, collapsed, onToggleCollapse, isDark, onToggleDark }) {
  return (
    <aside
      className={[
        'shrink-0 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full transition-all duration-200',
        collapsed ? 'w-10' : 'w-56',
      ].join(' ')}
    >
      {/* Header row with title + collapse toggle */}
      <div className="flex items-center justify-between px-3 py-4 border-b border-gray-200 dark:border-gray-700 min-h-[53px]">
        {!collapsed && (
          <h1 className="font-semibold text-gray-800 dark:text-gray-100 text-sm tracking-wide uppercase truncate">
            My Contacts
          </h1>
        )}
        <button
          onClick={onToggleCollapse}
          className="ml-auto text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-lg leading-none shrink-0"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      {/* Nav — hidden when collapsed */}
      {!collapsed && (
        <nav className="flex-1 min-h-0 overflow-y-auto py-2">
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

      {/* Bottom controls — always visible */}
      <div className={`border-t border-gray-200 dark:border-gray-700 ${collapsed ? 'flex flex-col items-center py-3 gap-3' : 'p-4 flex flex-col gap-3'}`}>
        {/* Dark mode toggle */}
        {collapsed ? (
          <button
            onClick={onToggleDark}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-lg leading-none"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? '☀' : '☾'}
          </button>
        ) : (
          <div className="flex items-center justify-between">
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

        {/* Sync button — expanded only */}
        {!isStatic && !collapsed && (
          <button
            onClick={onSync}
            disabled={syncing}
            className="w-full py-2 px-3 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300 transition-colors"
          >
            {syncing ? 'Syncing…' : 'Sync Contacts'}
          </button>
        )}
      </div>
    </aside>
  )
}
