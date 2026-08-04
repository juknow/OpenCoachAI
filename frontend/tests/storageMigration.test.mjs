import assert from 'node:assert/strict'
import test from 'node:test'

const values = new Map()
globalThis.window = {
  localStorage: {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  },
}

const { loadStoredCoachState, saveHistory } = await import(
  '../src/services/storageService.ts'
)

test('v1 history keeps raw and confirmed transcript meanings during migration', () => {
  values.clear()
  values.set(
    'opic-coach:v1:history',
    JSON.stringify([
      {
        id: 'legacy-session',
        firstAttempt: {
          transcript: {
            rawText: 'Um, I goed home.',
            editedText: 'Um, I went home.',
            provider: 'openai',
          },
          evaluation: { provider: 'openai' },
        },
      },
    ]),
  )

  const state = loadStoredCoachState()
  const transcript = state.history[0].firstAttempt.transcript
  assert.equal(transcript.rawTranscript, 'Um, I goed home.')
  assert.equal(transcript.confirmedTranscript, 'Um, I went home.')
  assert.equal(transcript.provider, 'local')
  assert.equal(state.history[0].firstAttempt.evaluation.provider, 'local')
})

test('new history is stored in a versioned envelope', () => {
  values.clear()
  saveHistory([])
  const envelope = JSON.parse(values.get('opic-coach:v2:history'))
  assert.deepEqual(envelope, { schemaVersion: 2, data: [] })
})
