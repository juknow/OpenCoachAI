export type QuestionType =
  | 'description'
  | 'routine'
  | 'past_experience'
  | 'comparison'
  | 'role_play'
  | 'problem_solution'

export type Difficulty = 'easy' | 'medium' | 'hard'

export type PracticeLevel =
  | 'NL'
  | 'NM'
  | 'NH'
  | 'IL'
  | 'IM1'
  | 'IM2'
  | 'IM3'
  | 'IH'
  | 'AL'

export type CoachProvider = 'mock' | 'local'

export type AppView =
  | 'landing'
  | 'profile'
  | 'home'
  | 'practice'
  | 'processing'
  | 'transcript'
  | 'feedback'
  | 'history'

export interface Question {
  id: string
  type: QuestionType
  difficulty: Difficulty
  topic: string
  prompt: string
  translation: string
}

export interface PracticeProfile {
  targetLevel: 'IM2' | 'IM3' | 'IH' | 'AL'
  currentLevel: 'unknown' | 'IM1' | 'IM2' | 'IM3' | 'IH'
  identity: 'student' | 'worker' | 'job_seeker'
  residence: 'family' | 'alone' | 'dormitory' | 'other'
  interests: string[]
  difficulty: Difficulty
}

export interface SpeechMetrics {
  durationSeconds: number
  shortPauses: number
  longPauses: number
  initialDelaySeconds: number
  silenceRatio: number
  energyVariation: number
  confidence: 'low' | 'medium'
  analysisSucceeded?: boolean
  peakRms?: number
  voicedFrameRatio?: number
}

export interface RecordingArtifact {
  blob: Blob
  url: string
  durationSeconds: number
  mimeType: string
  metrics: SpeechMetrics
}

export type RecordingPhase =
  | 'idle'
  | 'requesting'
  | 'recording'
  | 'recorded'
  | 'error'

export interface TranscriptResult {
  rawTranscript: string
  confirmedTranscript: string
  wordCount: number
  wpm: number
  fillerCount: number
  repeatedWordCount: number
  metrics: SpeechMetrics
  provider: CoachProvider
  requestId?: string
  transcriptionModel?: string
  serverMetrics?: import('./api.ts').ApiSpeechMetrics
}

export type RubricKey =
  | 'task'
  | 'content'
  | 'discourse'
  | 'timeFrame'
  | 'grammar'
  | 'vocabulary'
  | 'fluency'

export interface RubricScore {
  key: RubricKey
  label: string
  score: 0 | 1 | 2 | 3 | 4
  feedback: string
}

export interface ConversationDiagnostic {
  label: string
  score: 0 | 1 | 2 | 3 | 4
  feedback: string
}

export interface ExpressionSuggestion {
  situation: string
  expression: string
  guidance: string
}

export interface VocabularySuggestion {
  category: 'topic' | 'feeling' | 'action' | 'connector'
  phrase: string
  meaning: string
  guidance: string
  example: string
}

export interface ImprovementAnswer {
  variant: 'core' | 'next'
  sentenceCount: number
  wordCount: number
  text: string
  sentences?: string[]
}

export interface EvaluationResult {
  estimatedLevel: PracticeLevel
  estimatedRange: string
  confidence: '낮음' | '보통' | '높음'
  headline: string
  summary: string
  diagnostics: ConversationDiagnostic[]
  mainPointLabel: string
  mainPointFeedback: string
  feelingLanguage: string[]
  connectors: string[]
  expressions: ExpressionSuggestion[]
  vocabulary: VocabularySuggestion[]
  rubrics: RubricScore[]
  strengths: Array<{ title: string; detail: string; evidence: string }>
  blocker: { title: string; detail: string; evidence: string }
  corrections: Array<{ before: string; after: string; reason: string }>
  improvements: ImprovementAnswer[]
  reusableStructure: string[]
  retryMission: string[]
  provider: CoachProvider
  safetyNotice?: string
  metadata?: {
    requestId: string
    model: string
    inputTokens?: number
    outputTokens?: number
    cachedInputTokens?: number
    cacheWriteTokens?: number
    reasoningTokens?: number
    totalTokens?: number
  }
}

export interface AttemptResult {
  attempt: 1 | 2
  transcript: TranscriptResult
  evaluation: EvaluationResult
  completedAt: string
}

export interface ComparisonMetric {
  label: string
  before: string
  after: string
  direction: 'up' | 'same' | 'down'
}

export interface ComparisonResult {
  levelBefore: PracticeLevel
  levelAfter: PracticeLevel
  summary: string
  metrics: ComparisonMetric[]
  missionResults: Array<{ mission: string; achieved: boolean }>
  improvedAreas?: string[]
  remainingCoreIssue?: string
  recommendedNextQuestionType?: QuestionType
  provider: 'local'
}

export interface PracticeRecord {
  id: string
  question: Question
  profileSnapshot: PracticeProfile
  firstAttempt: AttemptResult
  retryAttempt?: AttemptResult
  comparison?: ComparisonResult
  createdAt: string
}

export interface ActiveSession {
  id: string
  question: Question
  profileSnapshot?: PracticeProfile
  attempt: 1 | 2
  transcript?: TranscriptResult
  firstAttempt?: AttemptResult
  retryAttempt?: AttemptResult
  comparison?: ComparisonResult
}

export interface ConnectionState {
  provider: CoachProvider
  preference: 'auto' | 'demo'
  backendStatus: 'checking' | 'ready' | 'unconfigured' | 'unreachable'
  readinessIssues?: string[]
  evaluationModel?: string
  transcriptionModel?: string
}

export interface CoachState {
  view: AppView
  profile: PracticeProfile | null
  connection: ConnectionState
  history: PracticeRecord[]
  session: ActiveSession | null
}

export type ProcessingStage =
  | 'upload'
  | 'transcribe'
  | 'evaluate'
  | 'improve'
