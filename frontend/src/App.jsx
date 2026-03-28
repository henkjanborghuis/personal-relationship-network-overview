import { useEffect, useState, useCallback } from 'react'
import { getAllContacts, getContactsMap, getGroups, syncContacts, IS_STATIC } from './api'
import GroupSidebar from './components/GroupSidebar'
import FamilyTreePanel from './components/FamilyTreePanel'
import InitialsCircle from './components/InitialsCircle'
import ContactDrawer from './components/ContactDrawer'

export default function App() {
  const [groups, setGroups] = useState([])
  const [contacts, setContacts] = useState({})   // uid → Contact
  const [allContacts, setAllContacts] = useState([]) // sorted list for "All" view
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [selectedUid, setSelectedUid] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [isDark, setIsDark] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
  }, [isDark])

  const loadData = useCallback(async () => {
    try {
      const [g, map, list] = await Promise.all([
        getGroups(),
        getContactsMap(),
        getAllContacts(),
      ])
      setGroups(g)
      setContacts(map)
      setAllContacts(list)
    } catch (e) {
      console.error('Failed to load data:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleSync = async () => {
    setSyncing(true)
    setSyncMsg(null)
    try {
      const result = await syncContacts()
      setSyncMsg(`Synced ${result.contacts_count} contacts across ${result.groups_count} groups.`)
      await loadData()
    } catch (e) {
      setSyncMsg(`Sync failed: ${e.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleSelectContact = (uid) => setSelectedUid(uid)
  const handleCloseDrawer = () => setSelectedUid(null)

  const selectedContact = selectedUid ? contacts[selectedUid] : null

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[100dvh] bg-white dark:bg-gray-950 text-gray-400 dark:text-gray-500">
        Loading contacts…
      </div>
    )
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-white dark:bg-gray-950 font-sans text-gray-900 dark:text-gray-100">
      <GroupSidebar
        groups={groups}
        selectedGroup={selectedGroup}
        onSelectGroup={setSelectedGroup}
        onSync={handleSync}
        syncing={syncing}
        isStatic={IS_STATIC}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(v => !v)}
        isDark={isDark}
        onToggleDark={() => setIsDark(v => !v)}
      />

      <main className="flex-1 overflow-y-auto relative">
        {/* Sync message banner */}
        {syncMsg && (
          <div className="sticky top-0 z-10 bg-green-50 dark:bg-green-900/30 border-b border-green-100 dark:border-green-800 px-6 py-2 text-sm text-green-700 dark:text-green-400 flex items-center justify-between">
            <span>{syncMsg}</span>
            <button onClick={() => setSyncMsg(null)} className="text-green-400 hover:text-green-600 ml-4">×</button>
          </div>
        )}

        {/* Group header */}
        {selectedGroup && (
          <div className="px-6 pt-5 pb-2 border-b border-gray-100 dark:border-gray-800">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">{selectedGroup}</h2>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-0.5">
              {groups.find(g => g.name === selectedGroup)?.count ?? 0} contacts
            </p>
          </div>
        )}

        {/* Group tree view */}
        {selectedGroup ? (
          <FamilyTreePanel
            groupName={selectedGroup}
            contacts={contacts}
            onSelectContact={handleSelectContact}
          />
        ) : (
          /* All contacts flat grid */
          <div className="p-6">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-1">All contacts</h2>
            <p className="text-sm text-gray-400 dark:text-gray-500 mb-5">{allContacts.length} people</p>
            <div className="flex flex-wrap gap-5">
              {allContacts.map(c => (
                <InitialsCircle
                  key={c.uid}
                  contact={c}
                  onSelect={handleSelectContact}
                />
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Detail drawer */}
      {selectedContact && (
        <ContactDrawer
          contact={selectedContact}
          contacts={contacts}
          onClose={handleCloseDrawer}
          onSelectContact={handleSelectContact}
        />
      )}
    </div>
  )
}
