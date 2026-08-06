import type {
  ApiDimensions,
  ApiEvaluationResult,
  ApiQuestionType,
  EvaluationRequest,
  EvaluationResponse,
  HigherAnswerRequest,
  HigherAnswerResponse,
  TranscriptionV3Response,
} from '../types/api.ts'
import type {
  EvaluationResult,
  PracticeProfile,
  Question,
  RubricKey,
  RubricScore,
} from '../types/coach.ts'
import type {
  CoachService,
  EvaluationInput,
  HigherAnswerInput,
  ProgressListener,
  TranscriptionInput,
} from './coachService.ts'
import { requestApi } from './apiClient.ts'
import {
  createTranscriptResult,
  splitSentences,
  toApiSpeechMetrics,
} from './transcriptMetricsService.ts'

const LOCAL_AI_GENERATION_TIMEOUT_MS = 1_260_000
const MAX_AUDIO_BYTES = 900_000

const MIME_EXTENSIONS: Record<string, string> = {
  'audio/webm': 'webm',
  'audio/mp4': 'mp4',
  'audio/mpeg': 'mp3',
  'audio/mp3': 'mp3',
  'audio/x-m4a': 'm4a',
  'audio/wav': 'wav',
  'audio/x-wav': 'wav',
}

const questionTypeForApi = (type: Question['type']): ApiQuestionType =>
  type === 'comparison' ? 'comparison_change' : type

const profileForApi = (profile: PracticeProfile): EvaluationRequest['profile'] => ({
  targetLevel: profile.targetLevel,
  currentLevel: profile.currentLevel,
  occupation: profile.identity === 'job_seeker' ? 'unemployed' : profile.identity,
  residence: profile.residence === 'dormitory' ? 'dorm' : profile.residence,
  interests: profile.interests,
  difficulty: profile.difficulty,
})

const questionForApi = (question: Question): EvaluationRequest['question'] => ({
  id: question.id,
  type: questionTypeForApi(question.type),
  topic: question.topic,
  difficulty: question.difficulty,
  question: question.prompt,
  koreanTranslation: question.translation,
  requiredElements: [question.prompt],
  relatedTopics: [question.topic],
})

const previousAttemptForApi = (
  input: EvaluationInput,
): EvaluationRequest['previousAttempt'] => {
  const previous = input.previousAttempt
  if (!previous) return null
  // Records saved by the earlier mock-only build used one combined
  // `grammarVocabulary` score. Preserve retry compatibility for those records.
  const scoreByKey = new Map<string, number>(
    previous.evaluation.rubrics.map((rubric) => [rubric.key, rubric.score]),
  )
  const legacyGrammarVocabulary = scoreByKey.get('grammarVocabulary') ?? 0
  const dimensionScores: Record<keyof ApiDimensions, number> = {
    taskCompletion: scoreByKey.get('task') ?? 0,
    contentSpecificity: scoreByKey.get('content') ?? 0,
    discourseOrganization: scoreByKey.get('discourse') ?? 0,
    timeFrameControl: scoreByKey.get('timeFrame') ?? 0,
    grammarControl: scoreByKey.get('grammar') ?? legacyGrammarVocabulary,
    vocabularyRange: scoreByKey.get('vocabulary') ?? legacyGrammarVocabulary,
    fluencyComprehensibility: scoreByKey.get('fluency') ?? 0,
  }
  const missions = previous.evaluation.retryMission
  return {
    level: previous.evaluation.estimatedLevel,
    dimensionScores,
    primaryBlocker: previous.evaluation.blocker.title,
    retryMission: [
      missions[0] ?? '핵심 내용을 먼저 말하기',
      missions[1] ?? '구체적인 근거 추가하기',
      missions[2] ?? '마무리 문장 말하기',
    ],
  }
}

const confidenceLabel = (value: ApiEvaluationResult['confidence']) =>
  value === 'low' ? '낮음' : value === 'medium' ? '보통' : '높음'

const mainPointLabel: Record<
  ApiEvaluationResult['conversationalDelivery']['mainPoint']['status'],
  string
> = {
  clear_early: '초반에 명확함',
  late: '뒤늦게 제시됨',
  missing: '중심 내용이 부족함',
  uncertain: '판단 근거가 제한적임',
}

const rubric = (
  key: RubricKey,
  label: string,
  value: { score: 0 | 1 | 2 | 3 | 4; reason: string },
): RubricScore => ({ key, label, score: value.score, feedback: value.reason })

const mapEvaluation = (response: EvaluationResponse): EvaluationResult => {
  const value = response.evaluation
  const delivery = value.conversationalDelivery
  const usage = response.metadata.usage
  return {
    estimatedLevel: value.mostLikelyLevel,
    estimatedRange: `${value.estimatedRange.lower} ~ ${value.estimatedRange.upper}`,
    confidence: confidenceLabel(value.confidence),
    headline: value.summaryKorean,
    summary: value.confidenceReason,
    diagnostics: [
      { label: '유창성', score: delivery.fluency.score, feedback: delivery.fluency.reason },
      { label: '정확성', score: delivery.accuracy.score, feedback: delivery.accuracy.reason },
      { label: '자연스러움', score: delivery.naturalness.score, feedback: delivery.naturalness.reason },
    ],
    mainPointLabel: mainPointLabel[delivery.mainPoint.status],
    mainPointFeedback: delivery.mainPoint.feedbackKorean,
    feelingLanguage: delivery.feelingExpressions,
    connectors: [
      ...new Set([
        ...delivery.functionalMarkers,
        ...delivery.disruptiveMarkers,
      ]),
    ],
    expressions: value.naturalPhraseSuggestions.map((item) => ({
      situation: item.contextKorean,
      expression: item.phraseEnglish,
      guidance: item.usageKorean,
    })),
    vocabulary: value.recommendedVocabulary.map((item) => ({
      category: item.category,
      phrase: item.wordOrPhraseEnglish,
      meaning: item.meaningKorean,
      guidance: item.whyRecommendedKorean,
      example: item.exampleSentenceEnglish,
    })),
    rubrics: [
      rubric('task', 'Task completion', value.dimensions.taskCompletion),
      rubric('content', 'Content & specificity', value.dimensions.contentSpecificity),
      rubric('discourse', 'Discourse & organization', value.dimensions.discourseOrganization),
      rubric('timeFrame', 'Time-frame control', value.dimensions.timeFrameControl),
      rubric('grammar', 'Grammar control', value.dimensions.grammarControl),
      rubric('vocabulary', 'Vocabulary range', value.dimensions.vocabularyRange),
      rubric('fluency', 'Fluency & comprehensibility', value.dimensions.fluencyComprehensibility),
    ],
    strengths: value.strengths.map((item) => ({
      title: item.title,
      detail: item.explanationKorean,
      evidence: item.evidenceFromTranscript,
    })),
    blocker: {
      title: value.primaryLevelBlocker.title,
      detail: value.primaryLevelBlocker.explanationKorean,
      evidence: value.primaryLevelBlocker.evidenceFromTranscript,
    },
    corrections: value.corrections.map((item) => ({
      before: item.original,
      after: item.corrected,
      reason: item.explanationKorean,
    })),
    improvements: [
      {
        variant: 'core',
        sentenceCount: value.baseAnswer.sentenceCount,
        wordCount: value.baseAnswer.wordCount,
        text: value.baseAnswer.sentences.join(' '),
        sentences: value.baseAnswer.sentences,
      },
    ],
    reusableStructure: value.reusableStructure.map(
      (item) => `${item.step}. ${item.titleKorean} — ${item.explanationKorean}`,
    ),
    retryMission: value.retryMission,
    provider: 'local',
    safetyNotice: value.safetyNoticeKorean,
    metadata: {
      requestId: response.metadata.requestId,
      model: response.metadata.model,
      inputTokens: usage?.inputTokens,
      outputTokens: usage?.outputTokens,
      cachedInputTokens: usage?.cachedInputTokens,
      cacheWriteTokens: usage?.cacheWriteTokens,
      reasoningTokens: usage?.reasoningTokens,
      totalTokens: usage?.totalTokens,
    },
  }
}

export const httpCoachService: CoachService = {
  async transcribe(input: TranscriptionInput, onProgress?: ProgressListener) {
    const mimeType = input.audio.type.split(';', 1)[0]?.toLowerCase() ?? ''
    const extension = MIME_EXTENSIONS[mimeType]
    if (!extension) throw new Error('지원하지 않는 녹음 형식입니다.')
    if (input.audio.size > MAX_AUDIO_BYTES) {
      throw new Error('녹음 파일이 900KB를 초과했습니다. 다시 녹음해 주세요.')
    }

    onProgress?.('upload')
    const formData = new FormData()
    formData.append('audio', input.audio, `opic-attempt-${input.attempt}.${extension}`)
    formData.append('durationSeconds', String(input.metrics.durationSeconds))
    formData.append('attemptNumber', String(input.attempt))
    onProgress?.('transcribe')
    const response = await requestApi<TranscriptionV3Response>('/api/v3/transcriptions', {
      method: 'POST',
      body: formData,
    })
    return createTranscriptResult(
      response.rawTranscript,
      input.metrics,
      'local',
      response.requestId,
      response.speechMetrics,
      response.model,
    )
  },

  async evaluate(input: EvaluationInput, onProgress?: ProgressListener) {
    onProgress?.('evaluate')
    const payload: EvaluationRequest = {
      profile: profileForApi(input.profile),
      question: questionForApi(input.question),
      attemptNumber: input.attempt,
      rawTranscript: input.transcript.rawTranscript,
      confirmedTranscript: input.transcript.confirmedTranscript,
      speechMetrics: toApiSpeechMetrics(input.transcript),
      previousAttempt: previousAttemptForApi(input),
    }
    const response = await requestApi<EvaluationResponse>(
      '/api/v3/evaluations',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      LOCAL_AI_GENERATION_TIMEOUT_MS,
    )
    onProgress?.('improve')
    return mapEvaluation(response)
  },

  async generateHigherAnswer(input: HigherAnswerInput) {
    const baseAnswer = input.evaluation.improvements.find(
      (answer) => answer.variant === 'core',
    )
    if (!baseAnswer) throw new Error('기본 개선 답변을 찾지 못했습니다.')

    const payload: HigherAnswerRequest = {
      profile: {
        targetLevel: input.profile.targetLevel,
        currentLevel: input.profile.currentLevel,
      },
      question: {
        type: questionTypeForApi(input.question.type),
        topic: input.question.topic,
        question: input.question.prompt,
      },
      transcript: input.transcript.confirmedTranscript,
      mostLikelyLevel: input.evaluation.estimatedLevel,
      baseAnswer: baseAnswer.sentences ?? splitSentences(baseAnswer.text),
    }
    const response = await requestApi<HigherAnswerResponse>(
      '/api/v3/improvements/higher',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      LOCAL_AI_GENERATION_TIMEOUT_MS,
    )
    return {
      variant: 'next',
      sentenceCount: response.answer.sentenceCount,
      wordCount: response.answer.wordCount,
      text: response.answer.sentences.join(' '),
      sentences: response.answer.sentences,
    }
  },
}
