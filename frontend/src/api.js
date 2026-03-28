/**
 * Data access layer.
 * In static mode (window.__APP_DATA__ defined), reads from the injected dataset.
 * In server mode, fetches from the FastAPI backend.
 */

const isStatic = typeof window !== 'undefined' && typeof window.__APP_DATA__ !== 'undefined'

function staticData() {
  return window.__APP_DATA__
}

export async function getGroups() {
  if (isStatic) return staticData().groups
  const res = await fetch('/api/groups')
  if (!res.ok) throw new Error('Failed to fetch groups')
  return res.json()
}

export async function getGroupView(groupName) {
  if (isStatic) return staticData().groupViews[groupName] ?? null
  const res = await fetch(`/api/groups/${encodeURIComponent(groupName)}`)
  if (!res.ok) throw new Error(`Failed to fetch group: ${groupName}`)
  return res.json()
}

export async function getAllContacts() {
  if (isStatic) return Object.values(staticData().contacts)
  const res = await fetch('/api/contacts')
  if (!res.ok) throw new Error('Failed to fetch contacts')
  return res.json()
}

export async function getContactsMap() {
  if (isStatic) return staticData().contacts
  const list = await getAllContacts()
  return Object.fromEntries(list.map(c => [c.uid, c]))
}

export async function syncContacts() {
  if (isStatic) throw new Error('Sync is not available in static export mode')
  const res = await fetch('/api/sync')
  if (!res.ok) throw new Error('Sync failed')
  return res.json()
}

export const IS_STATIC = isStatic
