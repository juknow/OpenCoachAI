import assert from 'node:assert/strict'
import test from 'node:test'
import { isEffectivelySilent } from '../src/services/audioAnalysisService.ts'

const metrics = {
  durationSeconds: 2,
  shortPauses: 0,
  longPauses: 0,
  initialDelaySeconds: 0,
  silenceRatio: 0,
  energyVariation: 0,
  confidence: 'low',
}

test('short audible recordings are not rejected by duration', () => {
  assert.equal(
    isEffectivelySilent({
      ...metrics,
      analysisSucceeded: true,
      peakRms: 0.03,
      voicedFrameRatio: 8,
    }),
    false,
  )
})

test('decoded recordings with no meaningful signal are rejected', () => {
  assert.equal(
    isEffectivelySilent({
      ...metrics,
      analysisSucceeded: true,
      peakRms: 0.001,
      voicedFrameRatio: 0,
    }),
    true,
  )
})

test('decode failures do not block potentially valid short recordings', () => {
  assert.equal(
    isEffectivelySilent({
      ...metrics,
      analysisSucceeded: false,
      peakRms: 0,
      voicedFrameRatio: 0,
    }),
    false,
  )
})
