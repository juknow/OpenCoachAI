import type {
  CoachProvider,
  SpeechMetrics,
  TranscriptResult,
} from '../types/coach.ts'
import type { ApiSpeechMetrics, ApiWordCount } from '../types/api.ts'

const FILLER_PATTERN = /\b(?:um+|uh+|er+|ah+|hmm+)\b/gi
const FUNCTIONAL_MARKERS = ['well', 'honestly', 'let me think', 'you know', 'i mean']

export const countWords = (text: string) =>
  text.trim() ? text.trim().split(/\s+/).length : 0

export const countSentences = (text: string) => {
  const matches = text.trim().match(/[^.!?]+[.!?]+|[^.!?]+$/g)
  return matches?.filter((sentence) => sentence.trim()).length ?? 0
}

export const countFillers = (text: string) => text.match(FILLER_PATTERN)?.length ?? 0

export const countRepeatedWords = (text: string) => {
  const words = text.toLowerCase().match(/[a-z']+/g) ?? []
  return words.reduce(
    (count, word, index) => count + (index > 0 && words[index - 1] === word ? 1 : 0),
    0,
  )
}

const countMatches = (text: string, values: string[]): ApiWordCount[] => {
  const lower = text.toLowerCase()
  return values.flatMap((value) => {
    const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const count = lower.match(new RegExp(`\\b${escaped}\\b`, 'g'))?.length ?? 0
    return count ? [{ word: value, count }] : []
  })
}

const fillerWordCounts = (text: string): ApiWordCount[] => {
  const counts = new Map<string, number>()
  for (const match of text.toLowerCase().match(FILLER_PATTERN) ?? []) {
    counts.set(match, (counts.get(match) ?? 0) + 1)
  }
  return [...counts].map(([word, count]) => ({ word, count }))
}

const repeatedPhrases = (text: string) => {
  const words = text.toLowerCase().match(/[a-z']+/g) ?? []
  const repetitions = new Set<string>()
  for (let index = 1; index < words.length; index += 1) {
    if (words[index] === words[index - 1] && words[index]) repetitions.add(words[index])
  }
  return [...repetitions].slice(0, 5)
}

export const createTranscriptResult = (
  rawText: string,
  metrics: SpeechMetrics,
  provider: CoachProvider,
  requestId?: string,
): TranscriptResult => {
  const wordCount = countWords(rawText)
  return {
    rawText,
    editedText: rawText,
    wordCount,
    wpm: Math.round(wordCount / Math.max(metrics.durationSeconds / 60, 1 / 60)),
    fillerCount: countFillers(rawText),
    repeatedWordCount: countRepeatedWords(rawText),
    metrics,
    provider,
    requestId,
  }
}

export const updateTranscriptText = (
  transcript: TranscriptResult,
  editedText: string,
): TranscriptResult => {
  const wordCount = countWords(editedText)
  return {
    ...transcript,
    editedText,
    wordCount,
    fillerCount: countFillers(editedText),
    repeatedWordCount: countRepeatedWords(editedText),
    wpm: Math.round(
      wordCount / Math.max(transcript.metrics.durationSeconds / 60, 1 / 60),
    ),
  }
}

export const toApiSpeechMetrics = (transcript: TranscriptResult): ApiSpeechMetrics => {
  const text = transcript.editedText
  const wordCount = countWords(text)
  const openingWordCount = Math.max(1, Math.round(transcript.wpm / 3))
  return {
    durationSeconds: transcript.metrics.durationSeconds,
    wordCount,
    wordsPerMinute: transcript.wpm,
    fillerWords: fillerWordCounts(text),
    repeatedPhrases: repeatedPhrases(text),
    functionalDiscourseMarkers: countMatches(text, FUNCTIONAL_MARKERS),
    fillerRatePer100Words: wordCount
      ? Number(((countFillers(text) / wordCount) * 100).toFixed(1))
      : 0,
    opening20SecondEstimate: text.split(/\s+/).slice(0, openingWordCount).join(' '),
    acoustic: {
      initialResponseDelaySeconds: transcript.metrics.initialDelaySeconds,
      hesitationPauseCount: transcript.metrics.shortPauses,
      longPauseCount: transcript.metrics.longPauses,
      silenceRatio: transcript.metrics.silenceRatio,
      energyVariationIndex: transcript.metrics.energyVariation,
      confidence: transcript.metrics.confidence,
    },
  }
}
