import assert from 'node:assert/strict'
import test from 'node:test'
import { MOCK_FEEDBACK_TEMPLATES } from '../src/data/mockFeedbackTemplates.ts'
import { countEnglishWords, countSentences } from '../src/services/transcriptMetricsService.ts'

test('all Demo Mode improvement answers keep the approved sentence and word ranges', () => {
  for (const [questionType, template] of Object.entries(MOCK_FEEDBACK_TEMPLATES)) {
    const coreText = template.coreSentences.join(' ')
    const higherText = template.nextSentences.join(' ')

    assert.ok(
      countSentences(coreText) >= 10 && countSentences(coreText) <= 12,
      `${questionType} core sentence count`,
    )
    assert.ok(
      countEnglishWords(coreText) >= 120 && countEnglishWords(coreText) <= 160,
      `${questionType} core word count`,
    )
    assert.ok(
      countSentences(higherText) >= 12 && countSentences(higherText) <= 15,
      `${questionType} higher sentence count`,
    )
    assert.ok(
      countEnglishWords(higherText) >= 140 && countEnglishWords(higherText) <= 180,
      `${questionType} higher word count`,
    )
  }
})
