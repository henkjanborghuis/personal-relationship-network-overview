import { useEffect, useState, useCallback, useRef } from 'react'
import { getAllContacts, getContactsMap, getGroups, getSettings, syncContacts, IS_STATIC } from './api'
import GroupSidebar from './components/GroupSidebar'
import FamilyTreePanel from './components/FamilyTreePanel'
import InitialsCircle from './components/InitialsCircle'
import ContactDrawer from './components/ContactDrawer'
import ZoomControls from './components/ZoomControls'
import LandscapeGuard from './components/LandscapeGuard'

const ZOOM_STEP = 0.15
const ZOOM_MIN = 0.15
const ZOOM_MAX = 2.0

export default function App() {
  const [groups, setGroups] = useState([])
  const [contacts, setContacts] = useState({})   // uid → Contact
  const [allContacts, setAllContacts] = useState([]) // sorted list for "All" view
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [selectedUid, setSelectedUid] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => window.innerWidth < 1024
  )
  const [isDark, setIsDark] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches
  )
  const [zoom, setZoom] = useState(1)

  // Refs for zoom measurement
  const viewportRef = useRef(null)   // the overflow-hidden clip container
  const contentRef = useRef(null)    // the CSS-zoom wrapper around FamilyTreePanel
  const naturalSizeRef = useRef({ w: 0, h: 0 })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
  }, [isDark])

  // Compute fit-to-screen zoom from stored natural dimensions
  const computeFit = useCallback(() => {
    if (!viewportRef.current) return 1
    const vp = viewportRef.current
    const { w: naturalW, h: naturalH } = naturalSizeRef.current
    if (naturalW <= 0 || naturalH <= 0) return 1
    const vpW = vp.clientWidth - 48   // account for padding
    const vpH = vp.clientHeight - 48
    const fit = Math.min(vpW / naturalW, vpH / naturalH, 1)
    return Math.max(ZOOM_MIN, fit)
  }, [])

  // Called by FamilyTreePanel after it finishes rendering — measure and auto-fit
  const handleReady = useCallback(() => {
    if (!contentRef.current) return
    const ct = contentRef.current
    // At this point zoom state is 1 (reset on group change), so offsetWidth = natural width
    naturalSizeRef.current = { w: ct.offsetWidth, h: ct.offsetHeight }
    setZoom(computeFit())
  }, [computeFit])

  const handleFit = useCallback(() => {
    setZoom(computeFit())
  }, [computeFit])

  // Reset zoom when group changes so handleReady measures at scale 1
  useEffect(() => {
    setZoom(1)
    naturalSizeRef.current = { w: 0, h: 0 }
  }, [selectedGroup])

  const loadData = useCallback(async () => {
    try {
      const [g, map, list, settings] = await Promise.all([
        getGroups(),
        getContactsMap(),
        getAllContacts(),
        getSettings(),
      ])
      setGroups(g)
      setContacts(map)
      setAllContacts(list)
      if (settings?.default_group) {
        setSelectedGroup(settings.default_group)
      }
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
  const handleSelectGroup = (name) => setSelectedGroup(name)

  const selectedContact = selectedUid ? contacts[selectedUid] : null

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[100dvh] bg-white dark:bg-gray-950 text-gray-400 dark:text-gray-500">
        Loading contacts…
      </div>
    )
  }

  return (
    <LandscapeGuard>
      <div className="flex h-[100dvh] overflow-hidden bg-white dark:bg-gray-950 font-sans text-gray-900 dark:text-gray-100" style={{ paddingLeft: 'env(safe-area-inset-left)', paddingRight: 'env(safe-area-inset-right)' }}>
        <GroupSidebar
          groups={groups}
          selectedGroup={selectedGroup}
          onSelectGroup={handleSelectGroup}
          onSync={handleSync}
          syncing={syncing}
          isStatic={IS_STATIC}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(v => !v)}
          isDark={isDark}
          onToggleDark={() => setIsDark(v => !v)}
        />

        <main className="flex-1 overflow-hidden flex flex-col">
          {/* Sync message banner */}
          {syncMsg && (
            <div className="shrink-0 bg-green-50 dark:bg-green-900/30 border-b border-green-100 dark:border-green-800 px-6 py-2 text-sm text-green-700 dark:text-green-400 flex items-center justify-between">
              <span>{syncMsg}</span>
              <button onClick={() => setSyncMsg(null)} className="text-green-400 hover:text-green-600 ml-4">×</button>
            </div>
          )}

          {/* Header: group selector dropdown */}
          <div className="shrink-0 px-6 pt-5 pb-3 border-b border-gray-100 dark:border-gray-800">
            <div className="relative inline-flex items-center gap-1">
              <select
                value={selectedGroup ?? ''}
                onChange={e => handleSelectGroup(e.target.value || null)}
                className="text-xl font-semibold text-gray-800 dark:text-gray-100 bg-transparent border-none outline-none cursor-pointer appearance-none pr-5 max-w-xs"
              >
                <option value="">All contacts</option>
                {groups.map(g => (
                  <option key={g.name} value={g.name}>{g.name}</option>
                ))}
              </select>
              <span className="pointer-events-none text-gray-400 dark:text-gray-500 text-sm -ml-4">▾</span>
            </div>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-0.5">
              {selectedGroup
                ? `${groups.find(g => g.name === selectedGroup)?.count ?? 0} contacts`
                : `${allContacts.length} contacts`}
            </p>
          </div>

          {/* Content area */}
          <div ref={viewportRef} className="flex-1 overflow-hidden relative">
            {selectedGroup ? (
              <>
                {/* Scaled family tree content */}
                <div className="absolute inset-0 overflow-auto p-6">
                  <div
                    ref={contentRef}
                    style={{ zoom, display: 'inline-block', minWidth: 'max-content' }}
                  >
                    <FamilyTreePanel
                      groupName={selectedGroup}
                      contacts={contacts}
                      onSelectContact={handleSelectContact}
                      onReady={handleReady}
                    />
                  </div>
                </div>

                {/* Zoom controls (floating, bottom-right) */}
                <ZoomControls
                  zoom={zoom}
                  onZoomIn={() => setZoom(z => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2)))}
                  onZoomOut={() => setZoom(z => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2)))}
                  onFit={handleFit}
                />
              </>
            ) : (
              /* All contacts flat grid */
              <div className="overflow-y-auto h-full p-6">
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
          </div>
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
    </LandscapeGuard>
  )
}
