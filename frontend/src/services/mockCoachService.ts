import { MOCK_FEEDBACK_TEMPLATES } from '../data/mockFeedbackTemplates.ts'
import type {
  EvaluationResult,
  ImprovementAnswer,
  PracticeLevel,
  RubricScore,
  TranscriptResult,
} from '../types/coach.ts'
import type {
  CoachService,
  EvaluationInput,
  ProgressListener,
  TranscriptionInput,
} from './coachService.ts'
import {
  countEnglishWords,
  countSentences,
  countWords,
  createTranscriptResult,
} from './transcriptMetricsService.ts'

const wait = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds))

const interpolate = (text: string, topic: string) =>
  text.replaceAll('{topic}', topic)

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
    ['grammar', 'Grammar control', 0],
    ['vocabulary', 'Vocabulary range', 0],
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
    wordCount: countEnglishWords(text),
    sentences: sentences.map((sentence) => interpolate(sentence, topic)),
  }
}

const feedbackFor = (score: RubricScore['score']) =>
  score === 0 ? '평가할 수 있는 발화 증거가 없습니다.' : scoreFeedback[score]

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
    return createTranscriptResult(rawText, input.metrics, 'mock')
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
        { label: '유창성', score: rubrics[6]?.score ?? 1, feedback: feedbackFor(rubrics[6]?.score ?? 1) },
        { label: '정확성', score: rubrics[4]?.score ?? 1, feedback: feedbackFor(rubrics[4]?.score ?? 1) },
        { label: '자연스러움', score: rubrics[2]?.score ?? 1, feedback: feedbackFor(rubrics[2]?.score ?? 1) },
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
      ],
      reusableStructure: template.reusableStructure,
      retryMission: template.retryMission,
      provider: 'mock',
    }
  },

  async generateHigherAnswer(input) {
    await wait(650)
    const template = MOCK_FEEDBACK_TEMPLATES[input.question.type]
    return buildImprovement(template.nextSentences, input.question.topic, 'next')
  },
}
