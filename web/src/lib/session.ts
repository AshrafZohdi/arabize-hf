// A random id per browser for the tutor's per-session message cap. Not linked to a person.
export function tutorSession(): string {
  const KEY = 'darby.tutorSession'
  try {
    const v = sessionStorage.getItem(KEY)
    if (v) return v
    const id = crypto.randomUUID()
    sessionStorage.setItem(KEY, id)
    return id
  } catch {
    return 'no-storage-' + Math.random().toString(36).slice(2, 12)
  }
}
