import assert from 'node:assert/strict'
import test from 'node:test'

import { compareAttempts } from '../src/services/comparisonService.ts'

const rubricKeys = [
  'task',
  'content',
  'discourse',
  'timeFrame',
  'grammar',
  'vocabulary',
  'fluency',
]

const attempt = (number, score, blocker) => ({
  attempt: number,
  transcript: {
    wordCount: number === 1 ? 80 : 95,
    wpm: number === 1 ? 90 : 98,
    metrics: { longPauses: number === 1 ? 3 : 2 },
  },
  evaluation: {
    estimatedLevel: number === 1 ? 'IM2' : 'IM3',
    rubrics: rubricKeys.map((key, index) => ({
      key,
      label: key,
      score: key === 'content' && number === 2 ? score + 1 : score,
      feedback: `${index}`,
    })),
    blocker: { title: blocker },
  },
})

test('retry comparison includes all seven deterministic rubric deltas', () => {
  const result = compareAttempts(
    attempt(1, 2, 'first blocker'),
    attempt(2, 2, 'specific detail'),
    ['mission one', 'mission two', 'mission three'],
  )

  assert.equal(
    result.metrics.filter((metric) => rubricKeys.includes(
      ({
        'Task completion': 'task',
        'Content & specificity': 'content',
        'Discourse & organization': 'discourse',
        'Time-frame control': 'timeFrame',
        'Grammar control': 'grammar',
        'Vocabulary range': 'vocabulary',
        'Fluency & comprehensibility': 'fluency',
      })[metric.label],
    )).length,
    7,
  )
  assert.deepEqual(result.improvedAreas, ['Content & specificity'])
  assert.equal(result.remainingCoreIssue, 'specific detail')
  assert.ok(result.recommendedNextQuestionType)
})
