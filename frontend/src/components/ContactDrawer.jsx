import InitialsCircle from './InitialsCircle'

function formatDate(isoDate) {
  if (!isoDate) return null
  // No-year format: --MM-DD
  if (isoDate.startsWith('--')) {
    const [, mm, dd] = isoDate.match(/--(\d{2})-?(\d{2})/) || []
    if (mm && dd) {
      const d = new Date(2000, parseInt(mm) - 1, parseInt(dd))
      return d.toLocaleDateString('en-NL', { month: 'long', day: 'numeric' })
    }
    return isoDate
  }
  try {
    const d = new Date(isoDate + 'T00:00:00')
    return d.toLocaleDateString('en-NL', { year: 'numeric', month: 'long', day: 'numeric' })
  } catch {
    return isoDate
  }
}

function age(birthday) {
  if (!birthday || birthday.startsWith('--')) return null
  const born = new Date(birthday)
  const today = new Date()
  let a = today.getFullYear() - born.getFullYear()
  const m = today.getMonth() - born.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < born.getDate())) a--
  return a
}

function Section({ title, children }) {
  return (
    <div className="mb-5">
      <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">{title}</p>
      {children}
    </div>
  )
}

export default function ContactDrawer({ contact, contacts, onClose, onSelectContact }) {
  if (!contact) return null

  const spouse = contact.spouse_uid ? contacts[contact.spouse_uid] : null
  const children = (contact.children_uids || []).map(uid => contacts[uid]).filter(Boolean)
  const parents = (contact.parent_uids || []).map(uid => contacts[uid]).filter(Boolean)
  const bday = formatDate(contact.birthday)
  const bdayAge = age(contact.birthday)
  const anniv = formatDate(contact.anniversary)

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer panel */}
      <aside className="fixed right-0 top-0 bottom-0 w-80 bg-white dark:bg-gray-900 shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <InitialsCircle contact={contact} size="lg" />
          <div className="flex-1 min-w-0">
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 text-base leading-tight">
              {contact.display_name}
            </h2>
            {contact.emails[0] && (
              <p className="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">{contact.emails[0]}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 shrink-0 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">

          {/* Birthday & Anniversary */}
          {(bday || anniv) && (
            <Section title="Dates">
              {bday && (
                <p className="text-sm text-gray-700 dark:text-gray-300 mb-1">
                  <span className="text-gray-400 mr-1">Birthday</span>
                  {bday}{bdayAge !== null && <span className="text-gray-400 ml-1">({bdayAge})</span>}
                </p>
              )}
              {anniv && (
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="text-gray-400 mr-1">Anniversary</span>
                  {anniv}
                </p>
              )}
            </Section>
          )}

          {/* Family */}
          {(spouse || children.length > 0 || parents.length > 0) && (
            <Section title="Family">
              {spouse && (
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs text-gray-400 dark:text-gray-500 w-16 shrink-0">Spouse</span>
                  <button
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline text-left"
                    onClick={() => onSelectContact(spouse.uid)}
                  >
                    {spouse.display_name}
                  </button>
                </div>
              )}
              {parents.length > 0 && (
                <div className="flex items-start gap-2 mb-2">
                  <span className="text-xs text-gray-400 dark:text-gray-500 w-16 shrink-0">Parents</span>
                  <div className="flex flex-col gap-0.5">
                    {parents.map(p => (
                      <button
                        key={p.uid}
                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline text-left"
                        onClick={() => onSelectContact(p.uid)}
                      >
                        {p.display_name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {children.length > 0 && (
                <div className="flex items-start gap-2">
                  <span className="text-xs text-gray-400 dark:text-gray-500 w-16 shrink-0">Children</span>
                  <div className="flex flex-col gap-0.5">
                    {children.map(c => (
                      <button
                        key={c.uid}
                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline text-left"
                        onClick={() => onSelectContact(c.uid)}
                      >
                        {c.display_name}
                        {c.birthday && !c.birthday.startsWith('--') && age(c.birthday) !== null && (
                          <span className="text-gray-400 ml-1 text-xs">({age(c.birthday)})</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </Section>
          )}

          {/* Interests */}
          {contact.interests?.length > 0 && (
            <Section title="Interests">
              <div className="flex flex-wrap gap-1.5">
                {contact.interests.map(i => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs rounded-full"
                  >
                    {i}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Notes */}
          {contact.notes && (
            <Section title="Notes">
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                {contact.notes}
              </p>
            </Section>
          )}

          {/* Contact details */}
          {contact.phone_numbers?.length > 0 && (
            <Section title="Phone">
              {contact.phone_numbers.map((p, i) => (
                <p key={i} className="text-sm text-gray-700 dark:text-gray-300">{p}</p>
              ))}
            </Section>
          )}

          {contact.emails?.length > 0 && (
            <Section title="Email">
              {contact.emails.map((e, i) => (
                <p key={i} className="text-sm text-gray-700 dark:text-gray-300 break-all">{e}</p>
              ))}
            </Section>
          )}
        </div>
      </aside>
    </>
  )
}
