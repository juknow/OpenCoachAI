import { MOCK_FEEDBACK_TEMPLATES } from '../data/mockFeedbackTemplates.ts'
import type {
  AttemptResult,
  ComparisonMetric,
  ComparisonResult,
  EvaluationResult,
  ImprovementAnswer,
  PracticeLevel,
  RubricScore,
  TranscriptResult,
} from '../types/coach.ts'
import type {
  CoachService,
  ComparisonInput,
  EvaluationInput,
  ProgressListener,
  TranscriptionInput,
} from './coachService.ts'

const wait = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds))

export const countWords = (text: string) =>
  text.trim() ? text.trim().split(/\s+/).length : 0

export const countSentences = (text: string) => {
  const matches = text.trim().match(/[^.!?]+[.!?]+|[^.!?]+$/g)
  return matches?.filter((sentence) => sentence.trim()).length ?? 0
}

const interpolate = (text: string, topic: string) =>
  text.replaceAll('{topic}', topic)

const countFillers = (text: string) =>
  text.match(/\b(?:um+|uh+|er+|ah+)\b/gi)?.length ?? 0

const countRepeatedWords = (text: string) => {
  const words = text.toLowerCase().match(/[a-z']+/g) ?? []
  return words.reduce(
    (count, word, index) => count + (index > 0 && words[index - 1] === word ? 1 : 0),
    0,
  )
}

const asScore = (value: number): 1 | 2 | 3 | 4 =>
  Math.max(1, Math.min(4, Math.round(value))) as 1 | 2 | 3 | 4

const practiceLevelFor = (wordCount: number, attempt: 1 | 2): PracticeLevel => {
  const adjusted = wordCount + (attempt === 2 ? 12 : 0)
  if (adjusted < 18) return 'NL'
  if (adjusted < 35) return 'NM'
  if (adjusted < 55) return 'NH'
  if (adjusted < 75) return 'IL'
  if (adjusted < 95) return 'IM1'
  if (adjusted < 120) return 'IM2'
  if (adjusted < 145) return 'IM3'
  if (adjusted < 175) return 'IH'
  return 'AL'
}

const scoreFeedback: Record<1 | 2 | 3 | 4, string> = {
  1: '평가에 필요한 발화 증거가 매우 제한적입니다.',
  2: '핵심 내용은 보이지만 구체성과 연결이 부족합니다.',
  3: '과업을 전반적으로 수행했으며 일부 표현을 다듬으면 좋습니다.',
  4: '구체적인 내용과 자연스러운 연결을 안정적으로 보여 줍니다.',
}

const buildRubrics = (
  wordCount: number,
  attempt: 1 | 2,
): RubricScore[] => {
  const base = wordCount < 20 ? 1 : wordCount < 55 ? 2 : wordCount < 105 ? 3 : 4
  const retryBonus = attempt === 2 ? 0.35 : 0
  const entries: Array<[RubricScore['key'], string, number]> = [
    ['task', 'Task completion', 0.15],
    ['content', 'Content & specificity', 0],
    ['discourse', 'Discourse & organization', -0.1],
    ['timeFrame', 'Time-frame control', -0.2],
    ['grammarVocabulary', 'Grammar & vocabulary', 0],
    ['fluency', 'Fluency & comprehensibility', -0.1],
  ]

  return entries.map(([key, label, offset]) => {
    const score = asScore(base + retryBonus + offset)
    return { key, label, score, feedback: scoreFeedback[score] }
  })
}

const buildImprovement = (
  sentences: string[],
  topic: string,
  variant: ImprovementAnswer['variant'],
): ImprovementAnswer => {
  const text = sentences.map((sentence) => interpolate(sentence, topic)).join(' ')
  return {
    variant,
    text,
    sentenceCount: countSentences(text),
    wordCount: countWords(text),
  }
}

const transcriptWithEditedText = (
  transcript: TranscriptResult,
  editedText: string,
): TranscriptResult => ({
  ...transcript,
  editedText,
  wordCount: countWords(editedText),
  fillerCount: countFillers(editedText),
  repeatedWordCount: countRepeatedWords(editedText),
  wpm: Math.round(
    countWords(editedText) / Math.max(transcript.metrics.durationSeconds / 60, 1 / 60),
  ),
})

export const updateTranscriptText = transcriptWithEditedText

const averageRubric = (attempt: AttemptResult) =>
  attempt.evaluation.rubrics.reduce((total, rubric) => total + rubric.score, 0) /
  attempt.evaluation.rubrics.length

const directionFor = (before: number, after: number): ComparisonMetric['direction'] =>
  after > before ? 'up' : after < before ? 'down' : 'same'

export const mockCoachService: CoachService = {
  async transcribe(
    input: TranscriptionInput,
    onProgress?: ProgressListener,
  ): Promise<TranscriptResult> {
    onProgress?.('upload')
    await wait(450)
    onProgress?.('transcribe')
    await wait(650)

    const template = MOCK_FEEDBACK_TEMPLATES[input.question.type]
    const rawText = interpolate(
      input.attempt === 1 ? template.transcript.first : template.transcript.retry,
      input.question.topic,
    )
    const wordCount = countWords(rawText)

    return {
      rawText,
      editedText: rawText,
      wordCount,
      wpm: Math.round(
        wordCount / Math.max(input.metrics.durationSeconds / 60, 1 / 60),
      ),
      fillerCount: countFillers(rawText),
      repeatedWordCount: countRepeatedWords(rawText),
      metrics: input.metrics,
      isMock: true,
    }
  },

  async evaluate(
    input: EvaluationInput,
    onProgress?: ProgressListener,
  ): Promise<EvaluationResult> {
    onProgress?.('evaluate')
    await wait(600)
    onProgress?.('improve')
    await wait(650)

    const template = MOCK_FEEDBACK_TEMPLATES[input.question.type]
    const topic = input.question.topic
    const wordCount = countWords(input.transcript.editedText)
    const rubrics = buildRubrics(wordCount, input.attempt)
    const level = practiceLevelFor(wordCount, input.attempt)
    const confidence = wordCount < 25 ? '낮음' : wordCount < 80 ? '보통' : '높음'

    return {
      estimatedLevel: level,
      estimatedRange: level === 'NL' ? 'NL ~ NM' : `${level} 중심`,
      confidence,
      headline:
        input.attempt === 2
          ? `재답변에서 구조가 더 분명해졌습니다. ${template.headline}`
          : template.headline,
      summary: template.summary,
      diagnostics: [
        { label: '유창성', score: rubrics[5]?.score ?? 1, feedback: scoreFeedback[rubrics[5]?.score ?? 1] },
        { label: '정확성', score: rubrics[4]?.score ?? 1, feedback: scoreFeedback[rubrics[4]?.score ?? 1] },
        { label: '자연스러움', score: rubrics[2]?.score ?? 1, feedback: scoreFeedback[rubrics[2]?.score ?? 1] },
      ],
      mainPointLabel: template.mainPointLabel,
      mainPointFeedback: template.mainPointFeedback,
      feelingLanguage: wordCount < 20 ? [] : ['I feel', 'I really like'],
      connectors: input.transcript.editedText.match(/\b(?:first|then|also|because|finally|however)\b/gi) ?? [],
      expressions: template.expressions.map((item) => ({
        ...item,
        expression: interpolate(item.expression, topic),
      })),
      vocabulary: template.vocabulary.map((item) => ({
        ...item,
        example: interpolate(item.example, topic),
      })),
      rubrics,
      strengths: [
        { title: '주제 응답', detail: '질문과 관련된 중심 소재를 제시했습니다.', evidence: input.transcript.editedText.split(/[.!?]/)[0]?.trim() || '응답 시작' },
        { title: '의사소통 시도', detail: '완벽하지 않아도 답변을 이어 가려는 흐름이 있습니다.', evidence: input.transcript.editedText.split(/[.!?]/)[1]?.trim() || '답변을 계속 이어 감' },
      ],
      blocker: {
        ...template.blocker,
        evidence: input.transcript.editedText.slice(0, 150),
      },
      corrections: [
        { before: 'It is nice and there are many things.', after: 'It has a welcoming atmosphere and several useful features.', reason: '일반적인 표현을 구체적인 명사와 형용사로 바꿉니다.' },
        { before: 'I go there sometimes because I like it.', after: 'I visit it twice a month because I can relax there.', reason: '빈도와 이유를 실제 정보로 확장합니다.' },
      ],
      improvements: [
        buildImprovement(template.coreSentences, topic, 'core'),
        buildImprovement(template.nextSentences, topic, 'next'),
      ],
      reusableStructure: template.reusableStructure,
      retryMission: template.retryMission,
      isMock: true,
    }
  },

  async compare(input: ComparisonInput): Promise<ComparisonResult> {
    await wait(350)
    const beforeWords = input.firstAttempt.transcript.wordCount
    const afterWords = input.retryAttempt.transcript.wordCount
    const beforeRubric = averageRubric(input.firstAttempt)
    const afterRubric = averageRubric(input.retryAttempt)

    return {
      levelBefore: input.firstAttempt.evaluation.estimatedLevel,
      levelAfter: input.retryAttempt.evaluation.estimatedLevel,
      summary:
        afterWords > beforeWords
          ? '재답변에서 발화량과 구조가 개선되었습니다. 다음에는 구체적인 예를 한 가지 더 추가해 보세요.'
          : '핵심 구조는 유지했지만 발화량 변화가 크지 않습니다. Retry Mission을 한 항목씩 다시 적용해 보세요.',
      metrics: [
        { label: '단어 수', before: `${beforeWords}`, after: `${afterWords}`, direction: directionFor(beforeWords, afterWords) },
        { label: 'WPM', before: `${input.firstAttempt.transcript.wpm}`, after: `${input.retryAttempt.transcript.wpm}`, direction: directionFor(input.firstAttempt.transcript.wpm, input.retryAttempt.transcript.wpm) },
        { label: '평균 평가', before: beforeRubric.toFixed(1), after: afterRubric.toFixed(1), direction: directionFor(beforeRubric, afterRubric) },
        { label: '긴 멈춤', before: `${input.firstAttempt.transcript.metrics.longPauses}`, after: `${input.retryAttempt.transcript.metrics.longPauses}`, direction: directionFor(input.retryAttempt.transcript.metrics.longPauses, input.firstAttempt.transcript.metrics.longPauses) },
      ],
      missionResults: input.missions.map((mission, index) => ({
        mission,
        achieved: index === 0 ? afterWords >= beforeWords : afterWords > beforeWords,
      })),
      isMock: true,
    }
  },
}

