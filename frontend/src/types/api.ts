import type { Difficulty, PracticeLevel } from './coach.ts'

export type ApiQuestionType =
  | 'description'
  | 'routine'
  | 'past_experience'
  | 'comparison_change'
  | 'role_play'
  | 'problem_solution'

export interface HealthResponse {
  status: 'ok'
}

export interface ConfigStatusResponse {
  openaiConfigured: boolean
}

export interface TranscriptionResponse {
  transcript: string
  requestId: string
}

export interface ApiWordCount {
  word: string
  count: number
}

export interface ApiSpeechMetrics {
  durationSeconds: number
  wordCount: number
  wordsPerMinute: number
  fillerWords: ApiWordCount[]
  repeatedPhrases: string[]
  functionalDiscourseMarkers: ApiWordCount[]
  fillerRatePer100Words: number
  opening20SecondEstimate: string
  acoustic: {
    initialResponseDelaySeconds: number
    hesitationPauseCount: number
    longPauseCount: number
    silenceRatio: number
    energyVariationIndex: number
    confidence: 'low' | 'medium'
  }
}

export interface ApiDimensionEvaluation {
  score: 0 | 1 | 2 | 3 | 4
  reason: string
}

export interface ApiDimensions {
  taskCompletion: ApiDimensionEvaluation
  contentSpecificity: ApiDimensionEvaluation
  discourseOrganization: ApiDimensionEvaluation
  timeFrameControl: ApiDimensionEvaluation
  grammarControl: ApiDimensionEvaluation
  vocabularyRange: ApiDimensionEvaluation
  fluencyComprehensibility: ApiDimensionEvaluation
}

export interface ApiEvidence {
  title: string
  explanationKorean: string
  evidenceFromTranscript: string
}

export interface EvaluationRequest {
  profile: {
    targetLevel: 'IM2' | 'IM3' | 'IH' | 'AL'
    currentLevel: 'unknown' | 'IM1' | 'IM2' | 'IM3' | 'IH'
    occupation: 'student' | 'worker' | 'unemployed'
    residence: 'family' | 'alone' | 'dorm' | 'other'
    interests: string[]
    difficulty: Difficulty
  }
  question: {
    id: string
    type: ApiQuestionType
    topic: string
    difficulty: Difficulty
    question: string
    koreanTranslation: string
    requiredElements: string[]
    relatedTopics: string[]
  }
  attemptNumber: 1 | 2
  transcript: string
  speechMetrics: ApiSpeechMetrics
  previousAttempt: {
    level: PracticeLevel
    dimensionScores: Record<keyof ApiDimensions, number>
    primaryBlocker: string
    retryMission: [string, string, string]
  } | null
}

export interface ApiImprovementAnswer {
  variant: 'core' | 'next'
  sentences: string[]
  sentenceCount: number
  wordCount: number
}

export interface ApiEvaluationResult {
  mostLikelyLevel: PracticeLevel
  confidence: 'low' | 'medium' | 'high'
  confidenceReason: string
  summaryKorean: string
  dimensions: ApiDimensions
  conversationalDelivery: {
    fluency: ApiDimensionEvaluation
    accuracy: ApiDimensionEvaluation
    naturalness: ApiDimensionEvaluation
    mainPoint: {
      status: 'clear_early' | 'late' | 'missing' | 'uncertain'
      feedbackKorean: string
    }
    feelingExpressions: string[]
    functionalMarkers: string[]
    disruptiveMarkers: string[]
  }
  naturalPhraseSuggestions: Array<{
    contextKorean: string
    phraseEnglish: string
    usageKorean: string
  }>
  recommendedVocabulary: Array<{
    category: 'topic' | 'feeling' | 'action' | 'connector'
    wordOrPhraseEnglish: string
    meaningKorean: string
    whyRecommendedKorean: string
    exampleSentenceEnglish: string
  }>
  strengths: ApiEvidence[]
  primaryLevelBlocker: ApiEvidence
  corrections: Array<{
    original: string
    corrected: string
    explanationKorean: string
  }>
  retryMission: [string, string, string]
  baseAnswer: ApiImprovementAnswer
  estimatedRange: { lower: PracticeLevel; upper: PracticeLevel }
  reusableStructure: Array<{
    step: number
    titleKorean: string
    explanationKorean: string
  }>
  safetyNoticeKorean: string
}

export interface EvaluationResponse {
  evaluation: ApiEvaluationResult
  metadata: {
    requestId: string
    model: string
    usage: {
      inputTokens: number
      outputTokens: number
      cachedInputTokens: number
      cacheWriteTokens?: number
      reasoningTokens?: number
      totalTokens?: number
    } | null
  }
}

export interface HigherAnswerRequest {
  profile: {
    targetLevel: 'IM2' | 'IM3' | 'IH' | 'AL'
    currentLevel: 'unknown' | 'IM1' | 'IM2' | 'IM3' | 'IH'
  }
  question: {
    type: ApiQuestionType
    topic: string
    question: string
  }
  transcript: string
  mostLikelyLevel: PracticeLevel
  baseAnswer: string[]
}

export interface HigherAnswerResponse {
  answer: ApiImprovementAnswer
  metadata: EvaluationResponse['metadata']
}

export interface ApiErrorResponse {
  error: {
    code: string
    message: string
    requestId: string
  }
}
