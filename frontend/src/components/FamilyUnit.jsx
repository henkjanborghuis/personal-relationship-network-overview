import InitialsCircle from './InitialsCircle'

export default function FamilyUnit({ unit, contacts, onSelect }) {
  const { couple, children } = unit

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-4 flex flex-col gap-3 min-w-[120px]">
      {/* Parents / couple */}
      <div className="flex gap-3 justify-center flex-wrap">
        {couple.map(uid => (
          <InitialsCircle key={uid} contact={contacts[uid]} onSelect={onSelect} />
        ))}
      </div>

      {/* Children */}
      {children.length > 0 && (
        <>
          <div className="border-t border-gray-100" />
          <div className="flex gap-3 justify-center flex-wrap">
            {children.map(uid => (
              <InitialsCircle key={uid} contact={contacts[uid]} onSelect={onSelect} size="sm" />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
