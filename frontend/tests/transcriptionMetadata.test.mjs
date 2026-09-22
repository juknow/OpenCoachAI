import assert from 'node:assert/strict'
import test from 'node:test'

import { createTranscriptResult } from '../src/services/transcriptMetricsService.ts'

const metrics = {
  durationSeconds: 12,
  shortPauses: 1,
  longPauses: 0,
  initialDelaySeconds: 0.4,
  silenceRatio: 18,
  energyVariation: 22,
  confidence: 'medium',
}

test('transcription metadata is preserved with the transcript result', () => {
  const metadata = {
    requestId: 'request-123',
    model: 'gpt-4o-mini-transcribe-2025-12-15',
    audioSeconds: 11.8,
    inputTokens: 70,
    outputTokens: 14,
    cachedInputTokens: 0,
    totalTokens: 84,
  }

  const transcript = createTranscriptResult(
    'Um, I I went there.',
    metrics,
    'openai',
    metadata,
  )

  assert.deepEqual(transcript.metadata, metadata)
  assert.equal(transcript.rawText, 'Um, I I went there.')
})

test('demo transcripts remain valid without API metadata', () => {
  const transcript = createTranscriptResult('I went there.', metrics, 'mock')

  assert.equal(transcript.metadata, undefined)
})
