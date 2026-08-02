import type { SpeechMetrics } from '../types/coach.ts'

const fallbackMetrics = (durationSeconds: number): SpeechMetrics => ({
  durationSeconds,
  shortPauses: 0,
  longPauses: 0,
  initialDelaySeconds: 0,
  silenceRatio: 0,
  energyVariation: 0,
  confidence: 'low',
})

export const analyzeAudio = async (
  blob: Blob,
  measuredDurationSeconds: number,
): Promise<SpeechMetrics> => {
  const AudioContextClass = window.AudioContext
  if (!AudioContextClass) return fallbackMetrics(measuredDurationSeconds)

  const context = new AudioContextClass()
  try {
    const buffer = await context.decodeAudioData(await blob.arrayBuffer())
    const samples = buffer.getChannelData(0)
    const durationSeconds = buffer.duration || measuredDurationSeconds
    const frameSeconds = 0.05
    const frameSize = Math.max(1, Math.floor(buffer.sampleRate * frameSeconds))
    const rmsValues: number[] = []

    for (let offset = 0; offset < samples.length; offset += frameSize) {
      let squareSum = 0
      const end = Math.min(offset + frameSize, samples.length)
      for (let index = offset; index < end; index += 1) {
        const sample = samples[index] ?? 0
        squareSum += sample * sample
      }
      rmsValues.push(Math.sqrt(squareSum / Math.max(1, end - offset)))
    }

    const peak = Math.max(...rmsValues, 0)
    const silenceThreshold = Math.max(0.008, peak * 0.08)
    const silentFrames = rmsValues.map((value) => value < silenceThreshold)
    const firstSoundFrame = silentFrames.findIndex((silent) => !silent)
    const initialDelaySeconds =
      firstSoundFrame < 0 ? durationSeconds : firstSoundFrame * frameSeconds
    let shortPauses = 0
    let longPauses = 0
    let silenceRun = 0

    const finishRun = (run: number) => {
      const pauseSeconds = run * frameSeconds
      if (pauseSeconds >= 0.28 && pauseSeconds <= 0.9) shortPauses += 1
      else if (pauseSeconds > 0.9) longPauses += 1
    }

    for (const silent of silentFrames) {
      if (silent) silenceRun += 1
      else if (silenceRun > 0) {
        finishRun(silenceRun)
        silenceRun = 0
      }
    }
    if (silenceRun > 0) finishRun(silenceRun)

    const silentCount = silentFrames.filter(Boolean).length
    const average =
      rmsValues.reduce((total, value) => total + value, 0) /
      Math.max(1, rmsValues.length)
    const variance =
      rmsValues.reduce((total, value) => total + (value - average) ** 2, 0) /
      Math.max(1, rmsValues.length)

    return {
      durationSeconds,
      shortPauses,
      longPauses,
      initialDelaySeconds: Number(initialDelaySeconds.toFixed(1)),
      silenceRatio: Math.round((silentCount / Math.max(1, silentFrames.length)) * 100),
      energyVariation: Math.round(Math.min(100, Math.sqrt(variance) * 1400)),
      confidence: peak > 0.02 ? 'medium' : 'low',
    }
  } catch {
    return fallbackMetrics(measuredDurationSeconds)
  } finally {
    await context.close()
  }
}
