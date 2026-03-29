import { useEffect, useState } from 'react'
import { getGroupView } from '../api'
import FamilyTreeNode from './FamilyTreeNode'
import InitialsCircle from './InitialsCircle'

export default function FamilyTreePanel({ groupName, contacts, onSelectContact, onReady }) {
  const [view, setView] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!groupName) return
    setLoading(true)
    setError(null)
    setView(null)
    getGroupView(groupName)
      .then(setView)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [groupName])

  // Notify parent once the view has rendered so it can measure and auto-fit
  useEffect(() => {
    if (view) {
      requestAnimationFrame(() => onReady?.())
    }
  }, [view, onReady])

  if (!groupName) return null

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 dark:text-gray-500 text-sm">
        Loading…
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-40 text-red-400 dark:text-red-500 text-sm">
        {error}
      </div>
    )
  }

  if (!view) return null

  const hasContent = view.trees?.length > 0 || view.singles?.length > 0

  if (!hasContent) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
        No contacts in this group yet.
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex flex-wrap gap-10 content-start items-start">
        {/* Family trees */}
        {view.trees?.map((tree, i) => (
          <FamilyTreeNode
            key={i}
            node={tree}
            contacts={contacts}
            onSelect={onSelectContact}
          />
        ))}
      </div>

      {/* Standalone contacts (not in any family structure) */}
      {view.singles?.length > 0 && (
        <>
          {view.trees?.length > 0 && (
            <div className="w-full border-t border-dashed border-gray-200 dark:border-gray-700 mt-4 mb-6" />
          )}
          <div className="flex flex-wrap gap-5">
            {view.singles.map(uid => (
              <InitialsCircle
                key={uid}
                contact={contacts[uid]}
                onSelect={onSelectContact}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
