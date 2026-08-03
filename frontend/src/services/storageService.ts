import type {
  ConnectionState,
  PracticeProfile,
  PracticeRecord,
} from '../types/coach.ts'

const PROFILE_KEY = 'opic-coach:v1:profile'
const CONNECTION_KEY = 'opic-coach:v2:provider-preference'
const HISTORY_KEY = 'opic-coach:v1:history'

const read = <T>(key: string, fallback: T): T => {
  try {
    const value = window.localStorage.getItem(key)
    return value ? (JSON.parse(value) as T) : fallback
  } catch {
    return fallback
  }
}

const write = (key: string, value: unknown) => {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // The app remains usable when storage is unavailable or full.
  }
}

export interface StoredCoachState {
  profile: PracticeProfile | null
  connection: ConnectionState
  history: PracticeRecord[]
}

export const loadStoredCoachState = (): StoredCoachState => ({
  profile: read<PracticeProfile | null>(PROFILE_KEY, null),
  connection: {
    provider: 'mock',
    preference: read<{ preference: 'auto' | 'demo' }>(CONNECTION_KEY, {
      preference: 'auto',
    }).preference,
    backendStatus: 'checking',
  },
  history: read<PracticeRecord[]>(HISTORY_KEY, []),
})

export const saveProfile = (profile: PracticeProfile | null) => {
  if (profile) write(PROFILE_KEY, profile)
  else window.localStorage.removeItem(PROFILE_KEY)
}

export const saveConnection = (connection: ConnectionState) => {
  write(CONNECTION_KEY, { preference: connection.preference })
}

export const saveHistory = (history: PracticeRecord[]) => {
  write(HISTORY_KEY, history)
}
