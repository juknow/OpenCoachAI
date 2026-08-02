import type {
  AttemptResult,
  ComparisonResult,
  EvaluationResult,
  PracticeProfile,
  ProcessingStage,
  Question,
  SpeechMetrics,
  TranscriptResult,
} from '../types/coach.ts'

export type ProgressListener = (stage: ProcessingStage) => void

export interface TranscriptionInput {
  audio: Blob
  question: Question
  attempt: 1 | 2
  metrics: SpeechMetrics
}

export interface EvaluationInput {
  question: Question
  profile: PracticeProfile
  transcript: TranscriptResult
  attempt: 1 | 2
}

export interface ComparisonInput {
  firstAttempt: AttemptResult
  retryAttempt: AttemptResult
  missions: string[]
}

export interface CoachService {
  transcribe(
    input: TranscriptionInput,
    onProgress?: ProgressListener,
  ): Promise<TranscriptResult>
  evaluate(
    input: EvaluationInput,
    onProgress?: ProgressListener,
  ): Promise<EvaluationResult>
  compare(input: ComparisonInput): Promise<ComparisonResult>
}
