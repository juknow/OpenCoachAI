import type {
  ConnectionState,
  PracticeProfile,
  PracticeRecord,
} from '../types/coach.ts'

const PROFILE_KEY = 'opic-coach:v1:profile'
const CONNECTION_KEY = 'opic-coach:v2:provider-preference'
const HISTORY_KEY = 'opic-coach:v1:history'
const PROFILE_V2_KEY = 'opic-coach:v2:profile'
const CONNECTION_V3_KEY = 'opic-coach:v3:provider-preference'
const HISTORY_V2_KEY = 'opic-coach:v2:history'

interface StorageEnvelope<T> {
  schemaVersion: 2
  data: T
}

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

const isObject = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === 'object' && !Array.isArray(value)

const readVersioned = <T>(key: string): T | undefined => {
  const envelope = read<StorageEnvelope<T> | null>(key, null)
  return envelope?.schemaVersion === 2 ? envelope.data : undefined
}

const migrateTranscript = (value: unknown) => {
  if (!isObject(value)) return value
  return {
    ...value,
    rawTranscript: String(value.rawTranscript ?? value.rawText ?? ''),
    confirmedTranscript: String(
      value.confirmedTranscript ?? value.editedText ?? value.rawText ?? '',
    ),
    provider: value.provider === 'mock' ? 'mock' : 'local',
  }
}

const migrateAttempt = (value: unknown) => {
  if (!isObject(value)) return value
  const evaluation = isObject(value.evaluation)
    ? {
        ...value.evaluation,
        provider: value.evaluation.provider === 'mock' ? 'mock' : 'local',
      }
    : value.evaluation
  return { ...value, transcript: migrateTranscript(value.transcript), evaluation }
}

const migrateHistory = (value: unknown): PracticeRecord[] => {
  if (!Array.isArray(value)) return []
  return value
    .filter(isObject)
    .map((record) => ({
      ...record,
      firstAttempt: migrateAttempt(record.firstAttempt),
      retryAttempt: record.retryAttempt
        ? migrateAttempt(record.retryAttempt)
        : undefined,
    })) as unknown as PracticeRecord[]
}

export interface StoredCoachState {
  profile: PracticeProfile | null
  connection: ConnectionState
  history: PracticeRecord[]
}

export const loadStoredCoachState = (): StoredCoachState => ({
  profile:
    readVersioned<PracticeProfile | null>(PROFILE_V2_KEY) ??
    read<PracticeProfile | null>(PROFILE_KEY, null),
  connection: {
    provider: 'mock',
    preference:
      readVersioned<{ preference: 'auto' | 'demo' }>(CONNECTION_V3_KEY)
        ?.preference ??
      read<{ preference: 'auto' | 'demo' }>(CONNECTION_KEY, {
        preference: 'auto',
      }).preference,
    backendStatus: 'checking',
  },
  history: migrateHistory(
    readVersioned<PracticeRecord[]>(HISTORY_V2_KEY) ??
      read<unknown>(HISTORY_KEY, []),
  ),
})

export const saveProfile = (profile: PracticeProfile | null) => {
  write(PROFILE_V2_KEY, { schemaVersion: 2, data: profile })
}

export const saveConnection = (connection: ConnectionState) => {
  write(CONNECTION_V3_KEY, {
    schemaVersion: 2,
    data: { preference: connection.preference },
  })
}

export const saveHistory = (history: PracticeRecord[]) => {
  write(HISTORY_V2_KEY, { schemaVersion: 2, data: history })
}
