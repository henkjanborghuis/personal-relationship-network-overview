import InitialsCircle from './InitialsCircle'

/**
 * Recursive family tree node.
 *
 * Layout:
 *   - Couple box at top
 *   - Single child → straight vertical line down
 *   - Multiple children → vertical line + horizontal sibship bar + vertical drops
 *
 * Bloodline distinction:
 *   - Blood member  (child of the parent couple above) → full opacity
 *   - Married-in member                                 → dimmed (opacity-40)
 *   - Root nodes (no parent)                            → all full opacity
 */
export default function FamilyTreeNode({ node, contacts, onSelect, parentCoupleUids = [] }) {
  if (!node) return null

  const hasChildren = node.children?.length > 0
  const childCount   = node.children?.length ?? 0

  const line = 'bg-gray-300 dark:bg-gray-600'

  // ── Phantom node: siblings with no in-group parent ──
  if (node.couple.length === 0) {
    if (childCount <= 1) {
      return hasChildren
        ? <FamilyTreeNode node={node.children[0]} contacts={contacts} onSelect={onSelect} parentCoupleUids={[]} />
        : null
    }
    return (
      <div className="flex flex-col items-center">
        <div className="relative">
          <div className={`absolute top-0 inset-x-0 h-px ${line}`} />
          <div className="flex items-start">
            {node.children.map((child, i) => (
              <div key={i} className="flex flex-col items-center px-4">
                <div className={`w-px h-5 ${line}`} />
                <FamilyTreeNode
                  node={child}
                  contacts={contacts}
                  onSelect={onSelect}
                  parentCoupleUids={[]}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // A member is "blood" if they are a child of one of the parent couple's members.
  const isBlood = (uid) =>
    parentCoupleUids.length === 0 ||
    (contacts[uid]?.parent_uids?.some(p => parentCoupleUids.includes(p)) ?? false)

  return (
    <div className="flex flex-col items-center">

      {/* ── Couple / individual box ── */}
      <div className="flex items-end gap-3 px-3 py-2.5 rounded-2xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
        {node.couple.map(uid => (
          <div key={uid} className={isBlood(uid) ? '' : 'opacity-40'}>
            <InitialsCircle
              contact={contacts[uid]}
              onSelect={onSelect}
              size="sm"
            />
          </div>
        ))}
      </div>

      {/* ── Single child: straight drop ── */}
      {hasChildren && childCount === 1 && (
        <>
          <div className={`w-px h-8 ${line}`} />
          <FamilyTreeNode
            node={node.children[0]}
            contacts={contacts}
            onSelect={onSelect}
            parentCoupleUids={node.couple}
          />
        </>
      )}

      {/* ── Multiple children: fork with sibship line ── */}
      {hasChildren && childCount > 1 && (
        <>
          {/* Vertical from couple down to sibship line */}
          <div className={`w-px h-5 ${line}`} />

          {/* Relative wrapper so the absolute sibship line spans the children row */}
          <div className="relative">
            {/* Horizontal sibship line */}
            <div className={`absolute top-0 inset-x-0 h-px ${line}`} />

            {/* Children side by side */}
            <div className="flex items-start">
              {node.children.map((child, i) => (
                <div key={i} className="flex flex-col items-center px-4">
                  {/* Vertical drop from sibship line to child */}
                  <div className={`w-px h-5 ${line}`} />
                  <FamilyTreeNode
                    node={child}
                    contacts={contacts}
                    onSelect={onSelect}
                    parentCoupleUids={node.couple}
                  />
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
