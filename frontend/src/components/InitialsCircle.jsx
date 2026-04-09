const COLORS = [
  '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
  '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16',
  '#06B6D4', '#A855F7',
]

function colorFromName(name) {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return COLORS[Math.abs(hash) % COLORS.length]
}

export default function InitialsCircle({ contact, onSelect, size = 'md' }) {
  if (!contact) return null

  const sizes = {
    sm: { circle: 'w-10 h-10 text-sm', label: 'text-xs mt-1 w-12' },
    md: { circle: 'w-14 h-14 text-lg', label: 'text-xs mt-1 w-16' },
    lg: { circle: 'w-16 h-16 text-xl', label: 'text-sm mt-1 w-20' },
  }
  const s = sizes[size] || sizes.md
  const bg = colorFromName(contact.display_name)

  return (
    <div
      className="flex flex-col items-center cursor-pointer group"
      onClick={() => onSelect?.(contact.uid)}
      title={contact.display_name}
    >
      {contact.photo_url ? (
        <img
          src={contact.photo_url}
          alt={contact.display_name}
          className={`${s.circle} rounded-full object-cover shadow-sm group-hover:ring-2 group-hover:ring-offset-1 group-hover:ring-blue-400 transition-all select-none`}
        />
      ) : (
        <div
          className={`${s.circle} rounded-full flex items-center justify-center font-semibold text-white shadow-sm group-hover:ring-2 group-hover:ring-offset-1 group-hover:ring-blue-400 transition-all select-none`}
          style={{ backgroundColor: bg }}
        >
          {contact.initials}
        </div>
      )}
      <span className={`${s.label} text-center text-gray-600 dark:text-gray-400 truncate leading-tight`}>
        {contact.first_name || contact.display_name}{contact.death_date ? ' †' : ''}
      </span>
    </div>
  )
}
