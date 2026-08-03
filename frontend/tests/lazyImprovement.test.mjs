import assert from 'node:assert/strict'
import test from 'node:test'
import { coachReducer } from '../src/state/coachReducer.ts'

const core = {
  variant: 'core',
  sentenceCount: 10,
  wordCount: 130,
  text: 'Base answer.',
}

const higher = {
  variant: 'next',
  sentenceCount: 13,
  wordCount: 155,
  text: 'Higher answer.',
}

const firstAttempt = {
  attempt: 1,
  transcript: { editedText: 'Learner answer.' },
  evaluation: { improvements: [core] },
  completedAt: '2026-08-03T00:00:00.000Z',
}

const state = {
  view: 'feedback',
  profile: null,
  connection: { provider: 'mock', preference: 'demo', backendStatus: 'unconfigured' },
  session: {
    id: 'session-1',
    question: { id: 'q1' },
    attempt: 1,
    firstAttempt,
  },
  history: [
    {
      id: 'session-1',
      question: { id: 'q1' },
      profileSnapshot: {},
      firstAttempt,
      createdAt: '2026-08-03T00:00:00.000Z',
    },
  ],
}

test('a lazy higher answer is persisted in both the active session and history', () => {
  const updated = coachReducer(state, {
    type: 'SET_HIGHER_IMPROVEMENT',
    attempt: 1,
    answer: higher,
  })

  assert.deepEqual(updated.session.firstAttempt.evaluation.improvements, [core, higher])
  assert.deepEqual(updated.history[0].firstAttempt.evaluation.improvements, [core, higher])
})

test('reapplying a generated answer replaces it instead of creating duplicates', () => {
  const once = coachReducer(state, {
    type: 'SET_HIGHER_IMPROVEMENT',
    attempt: 1,
    answer: higher,
  })
  const refreshed = { ...higher, text: 'Regenerated higher answer.' }
  const twice = coachReducer(once, {
    type: 'SET_HIGHER_IMPROVEMENT',
    attempt: 1,
    answer: refreshed,
  })

  const improvements = twice.session.firstAttempt.evaluation.improvements
  assert.equal(improvements.filter((item) => item.variant === 'next').length, 1)
  assert.equal(improvements[1].text, 'Regenerated higher answer.')
})
