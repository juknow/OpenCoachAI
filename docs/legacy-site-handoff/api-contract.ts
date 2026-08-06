/**
 * OPIc AI Coach HTTP contract transcribed from deployed source version 12.
 *
 * This file describes the current wire contract so a React client and FastAPI
 * server can reproduce it. It contains no credential values.
 */

export const API_PATHS = {
  status: "/api/status",
  transcribe: "/api/transcribe",
  evaluate: "/api/evaluate",
  compare: "/api/compare",
} as const;

/**
 * Current browser-key mode sends this header to transcribe/evaluate only.
 * When a server-side OPENAI_API_KEY exists, the header is omitted.
 */
export const OPENAI_API_KEY_HEADER = "X-OpenAI-API-Key" as const;

export type QuestionType =
  | "description"
  | "routine"
  | "past_experience"
  | "comparison_change"
  | "role_play"
  | "problem_solution";

export type Difficulty = "easy" | "medium" | "hard";
export type PracticeLevel = "NL" | "NM" | "NH" | "IL" | "IM1" | "IM2" | "IM3" | "IH" | "AL";
export type Confidence = "low" | "medium" | "high";

export interface UserProfile {
  targetLevel: "IM2" | "IM3" | "IH" | "AL";
  currentLevel: "unknown" | "IM1" | "IM2" | "IM3" | "IH";
  occupation: "student" | "worker" | "unemployed";
  residence: "family" | "alone" | "dorm" | "other";
  interests: string[]; // request validation: maxItems 9
  difficulty: Difficulty;
}

export interface PracticeQuestion {
  id: string;
  type: QuestionType;
  topic: string;
  difficulty: Difficulty;
  question: string;
  koreanTranslation: string;
  requiredElements: string[];
  relatedTopics: string[];
}

export interface FillerWordCount {
  word: string;
  count: number;
}

export interface AcousticMetrics {
  initialResponseDelaySeconds: number;
  hesitationPauseCount?: number;
  averageHesitationPauseSeconds?: number;
  longPauseCount: number;
  averageLongPauseSeconds: number;
  silenceRatio: number;
  pitchRangeSemitones: number | null;
  energyVariationDb: number;
  confidence: Confidence;
}

export interface SpeechMetrics {
  durationSeconds: number;
  wordCount: number;
  wordsPerMinute: number;
  fillerWords: FillerWordCount[];
  repeatedPhrases: string[]; // maxItems 5
  functionalDiscourseMarkers?: FillerWordCount[];
  hesitationFillers?: FillerWordCount[];
  fillerRatePer100Words?: number;
  opening20SecondEstimate?: string;
  acoustic?: AcousticMetrics;
}

export interface DimensionEvaluation {
  score: 0 | 1 | 2 | 3 | 4;
  reason: string;
}

export interface Evidence {
  title: string;
  explanationKorean: string;
  evidenceFromTranscript: string;
}

export interface Correction {
  original: string;
  corrected: string;
  explanationKorean: string;
}

export interface EvaluationResult {
  mostLikelyLevel: PracticeLevel;
  estimatedRange: { lower: PracticeLevel; upper: PracticeLevel };
  confidence: Confidence;
  confidenceReason: string;
  summaryKorean: string;
  dimensions: {
    taskCompletion: DimensionEvaluation;
    contentSpecificity: DimensionEvaluation;
    discourseOrganization: DimensionEvaluation;
    timeFrameControl: DimensionEvaluation;
    grammarControl: DimensionEvaluation;
    vocabularyRange: DimensionEvaluation;
    fluencyComprehensibility: DimensionEvaluation;
  };
  conversationalDelivery: {
    fluency: DimensionEvaluation;
    accuracy: DimensionEvaluation;
    naturalness: DimensionEvaluation;
    mainPoint: {
      status: "clear_early" | "late" | "missing" | "uncertain";
      first20SecondsEstimate: string;
      feedbackKorean: string;
    };
    feelingLanguage: {
      expressions: string[]; // maxItems 4
      feedbackKorean: string;
    };
    discourseMarkers: {
      functional: string[]; // maxItems 4
      disruptive: string[]; // maxItems 4
      feedbackKorean: string;
    };
  };
  naturalPhraseSuggestions: [
    { contextKorean: string; phraseEnglish: string; usageKorean: string },
    { contextKorean: string; phraseEnglish: string; usageKorean: string },
  ];
  recommendedVocabulary: [
    RecommendedVocabulary,
    RecommendedVocabulary,
    RecommendedVocabulary,
  ];
  strengths: [Evidence, Evidence];
  /** The deployed API route replaces model limitations with an empty array. */
  limitations: Evidence[];
  primaryLevelBlocker: Evidence;
  corrections: Correction[]; // maxItems 3 in model output
  /** Server-joined 10–12 model sentence items. */
  minimalCorrectionVersion: string;
  /** Server-joined 12–15 model sentence items. */
  nextLevelVersion: string;
  /** Static server-side structure selected by question.type. */
  reusableStructure: Array<{
    step: number;
    titleKorean: string;
    explanationKorean: string;
  }>;
  retryMission: [string, string, string];
  recommendedNextQuestionType: QuestionType;
  safetyNoticeKorean: string;
}

export interface RecommendedVocabulary {
  category: "topic" | "feeling" | "action" | "connector";
  wordOrPhraseEnglish: string;
  meaningKorean: string;
  whyRecommendedKorean: string;
  exampleSentenceEnglish: string;
}

export interface StatusResponse {
  apiConfigured: boolean;
}

/**
 * POST /api/transcribe
 * Content-Type: multipart/form-data (browser supplies boundary)
 * fields:
 *   audio: File
 *   durationSeconds: decimal string
 *   attemptNumber: "1" | "2" (sent by browser; ignored by current route)
 */
export type TranscribeFormFields = {
  audio: File | Blob;
  durationSeconds: string;
  attemptNumber: "1" | "2";
};

export type TranscribeResponse = { transcript: string } & SpeechMetrics;

export interface PreviousEvaluationForRequest {
  mostLikelyLevel: PracticeLevel;
  dimensions: EvaluationResult["dimensions"];
  primaryLevelBlocker: Evidence;
  retryMission: [string, string, string];
  /** Additional EvaluationResult fields are accepted by the current passthrough schema. */
  [key: string]: unknown;
}

export interface EvaluateRequest {
  profile: UserProfile;
  question: PracticeQuestion;
  attemptNumber: 1 | 2;
  transcript: string; // minLength 1, maxLength 12000
  speechMetrics: SpeechMetrics;
  previousEvaluation?: PreviousEvaluationForRequest;
}

export type EvaluateResponse = EvaluationResult;

export interface PracticeAttemptPayload {
  transcript: string;
  speechMetrics: SpeechMetrics;
  evaluation: EvaluationResult;
}

export interface CompareRequest {
  question: PracticeQuestion;
  firstAttempt: PracticeAttemptPayload;
  secondAttempt: PracticeAttemptPayload;
}

export interface AttemptComparison {
  overallImproved: boolean;
  summaryKorean: string;
  levelChange: {
    before: PracticeLevel;
    after: PracticeLevel;
    explanationKorean: string;
  };
  dimensionChanges: Array<{
    dimension: string;
    before: number;
    after: number;
    explanationKorean: string;
  }>;
  improvedAreas: Array<{ title: string; evidenceKorean: string }>;
  remainingIssue: { title: string; explanationKorean: string };
  nextPracticeRecommendation: {
    questionType: QuestionType;
    reasonKorean: string;
  };
}

export type CompareResponse = AttemptComparison;

export interface ApiErrorResponse {
  code?:
    | "RECORDING_TOO_LARGE"
    | "OPENAI_CONNECTION_REQUIRED"
    | "OPENAI_QUOTA_EXCEEDED"
    | "OPENAI_RATE_LIMITED"
    | "OPENAI_INVALID_KEY"
    | "OPENAI_PERMISSION_DENIED"
    | "OPENAI_MODEL_UNAVAILABLE";
  error: string;
  actionLabel?: string;
  actionUrl?: string;
}

export interface PracticeAttempt {
  attemptNumber: 1 | 2;
  transcript: string;
  speechMetrics: SpeechMetrics;
  evaluation: EvaluationResult;
  createdAt: string;
}

/** Stored as one item in localStorage key "opic-ai-coach:sessions". */
export interface PracticeSession {
  id: string;
  createdAt: string;
  profileSnapshot: UserProfile;
  question: PracticeQuestion;
  firstAttempt: PracticeAttempt;
  secondAttempt?: PracticeAttempt;
  comparison?: AttemptComparison;
}
