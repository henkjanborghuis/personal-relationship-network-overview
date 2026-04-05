import { useEffect, useState } from 'react'
import { getGroupView } from '../api'
import InitialsCircle from './InitialsCircle'

export default function FamilyNavigator({ groupName, contacts, onSelect }) {
  const [loading, setLoading] = useState(false)
  const [groupView, setGroupView] = useState(null)
  const [focalUid, setFocalUid] = useState(null)
  const [history, setHistory] = useState([])

  // On group change, load the group view to find the starting focal contact
  useEffect(() => {
    if (!groupName) return
    setLoading(true)
    setGroupView(null)
    setFocalUid(null)
    setHistory([])
    getGroupView(groupName)
      .then(view => {
        setGroupView(view)
        if (view.trees.length > 1) {
          setFocalUid(null) // null = root level mode: show all roots
        } else {
          const first = view.trees?.[0]?.couple?.[0] ?? view.singles?.[0] ?? null
          setFocalUid(first)
        }
      })
      .finally(() => setLoading(false))
  }, [groupName])

  const navigateTo = (uid) => {
    if (!uid || uid === focalUid) return
    setHistory(h => [...h, focalUid])
    setFocalUid(uid)
  }

  const goBack = () => {
    if (history.length === 0) return
    setFocalUid(history[history.length - 1])
    setHistory(h => h.slice(0, -1))
  }

  if (loading || !groupView) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 dark:text-gray-500 text-sm">
        Loading…
      </div>
    )
  }

  // Root level mode: multiple root trees with no common ancestor — show each family separately
  if (!focalUid) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div className="shrink-0 px-4 py-2 border-b border-gray-100 dark:border-gray-800 flex items-center">
          <button
            disabled
            className="text-sm text-gray-300 dark:text-gray-600 font-medium"
          >
            ‹ Back
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col p-4">
            {groupView.trees.map((tree, idx) => {
              const rootSet = new Set(tree.couple)
              const childUids = tree.children.map(child =>
                child.couple.find(uid => contacts[uid]?.parent_uids?.some(p => rootSet.has(p)))
                ?? child.couple[0]
              )
              return (
                <div key={idx} className={idx > 0 ? 'border-t border-gray-100 dark:border-gray-800' : ''}>
                  <div className="py-4">
                    <div className="flex flex-wrap gap-3 px-3 py-2.5 rounded-2xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 shadow-sm">
                      {tree.couple.map(uid => contacts[uid] && (
                        <InitialsCircle key={uid} contact={contacts[uid]} onSelect={navigateTo} size="md" />
                      ))}
                    </div>
                  </div>
                  {childUids.length > 0 && (
                    <NavigatorRow
                      label="Children"
                      uids={childUids}
                      contacts={contacts}
                      onTap={navigateTo}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  const focal = contacts[focalUid]
  if (!focal) return null

  const spouseUid = focal.spouse_uid
  const spouse = spouseUid ? contacts[spouseUid] : null

  const parentUids = focal.parent_uids ?? []

  const grandparentUids = [...new Set(
    parentUids.flatMap(p => contacts[p]?.parent_uids ?? [])
  )]

  // Union of focal + spouse children, deduplicated
  const childUids = [...new Set([
    ...(focal.children_uids ?? []),
    ...(spouse?.children_uids ?? []),
  ])]

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Back navigation bar */}
      <div className="shrink-0 px-4 py-2 border-b border-gray-100 dark:border-gray-800 flex items-center">
        <button
          onClick={goBack}
          disabled={history.length === 0}
          className="text-sm text-blue-500 dark:text-blue-400 disabled:text-gray-300 dark:disabled:text-gray-600 font-medium"
        >
          ‹ Back
        </button>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col p-4">

          {grandparentUids.length > 0 && (
            <NavigatorRow
              label="Grandparents"
              uids={grandparentUids}
              contacts={contacts}
              onTap={navigateTo}
            />
          )}

          {parentUids.length > 0 && (
            <NavigatorRow
              label="Parents"
              uids={parentUids}
              contacts={contacts}
              onTap={navigateTo}
            />
          )}

          {/* Focal couple — highlighted, tapping opens detail drawer */}
          <div className="py-4">
            <div className="text-xs font-medium text-blue-500 dark:text-blue-400 uppercase tracking-wide mb-2">
              Viewing
            </div>
            <div className="flex items-end gap-3 px-3 py-2.5 rounded-2xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 shadow-sm self-start inline-flex">
              <InitialsCircle contact={focal} onSelect={onSelect} size="md" />
              {spouse && (
                <InitialsCircle contact={spouse} onSelect={onSelect} size="md" />
              )}
            </div>
          </div>

          {childUids.length > 0 && (
            <NavigatorRow
              label="Children"
              uids={childUids}
              contacts={contacts}
              onTap={navigateTo}
            />
          )}

        </div>
      </div>
    </div>
  )
}

function NavigatorRow({ label, uids, contacts, onTap }) {
  return (
    <div className="py-3 border-t border-gray-100 dark:border-gray-800">
      <div className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">
        {label}
      </div>
      <div className="flex flex-wrap gap-3">
        {uids.map(uid => {
          const c = contacts[uid]
          if (!c) return null
          return (
            <InitialsCircle
              key={uid}
              contact={c}
              onSelect={onTap}
              size="sm"
            />
          )
        })}
      </div>
    </div>
  )
}
