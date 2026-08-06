import type {
  AttemptResult,
  ComparisonMetric,
  ComparisonResult,
  QuestionType,
  RubricKey,
} from '../types/coach.ts'

const averageRubric = (attempt: AttemptResult) =>
  attempt.evaluation.rubrics.reduce((total, rubric) => total + rubric.score, 0) /
  Math.max(1, attempt.evaluation.rubrics.length)

const directionFor = (before: number, after: number): ComparisonMetric['direction'] =>
  after > before ? 'up' : after < before ? 'down' : 'same'

const RUBRIC_LABELS: Record<RubricKey, string> = {
  task: 'Task completion',
  content: 'Content & specificity',
  discourse: 'Discourse & organization',
  timeFrame: 'Time-frame control',
  grammar: 'Grammar control',
  vocabulary: 'Vocabulary range',
  fluency: 'Fluency & comprehensibility',
}

const NEXT_TYPE_BY_RUBRIC: Record<RubricKey, QuestionType> = {
  task: 'role_play',
  content: 'description',
  discourse: 'routine',
  timeFrame: 'past_experience',
  grammar: 'comparison',
  vocabulary: 'description',
  fluency: 'routine',
}

const rubricScores = (attempt: AttemptResult) =>
  new Map(attempt.evaluation.rubrics.map((rubric) => [rubric.key, rubric.score]))

export const compareAttempts = (
  firstAttempt: AttemptResult,
  retryAttempt: AttemptResult,
  missions: string[],
): ComparisonResult => {
  const beforeWords = firstAttempt.transcript.wordCount
  const afterWords = retryAttempt.transcript.wordCount
  const beforeRubric = averageRubric(firstAttempt)
  const afterRubric = averageRubric(retryAttempt)
  const beforeScores = rubricScores(firstAttempt)
  const afterScores = rubricScores(retryAttempt)
  const rubricMetrics = (Object.keys(RUBRIC_LABELS) as RubricKey[]).map((key) => {
    const before = beforeScores.get(key) ?? 0
    const after = afterScores.get(key) ?? 0
    return {
      label: RUBRIC_LABELS[key],
      before: `${before}`,
      after: `${after}`,
      direction: directionFor(before, after),
    }
  })
  const improvedAreas = rubricMetrics
    .filter((metric) => metric.direction === 'up')
    .map((metric) => metric.label)
  const weakestRubric = (Object.keys(RUBRIC_LABELS) as RubricKey[]).reduce(
    (weakest, key) =>
      (afterScores.get(key) ?? 0) < (afterScores.get(weakest) ?? 0) ? key : weakest,
    'task',
  )

  return {
    levelBefore: firstAttempt.evaluation.estimatedLevel,
    levelAfter: retryAttempt.evaluation.estimatedLevel,
    summary:
      afterRubric > beforeRubric
        ? '재답변에서 평가 차원의 평균이 개선되었습니다. 향상된 영역을 유지하면서 남은 핵심 문제를 연습해 보세요.'
        : '평가 차원의 평균은 유지되거나 낮아졌습니다. Retry Mission을 하나씩 적용해 다시 구조화해 보세요.',
    metrics: [
      {
        label: '단어 수',
        before: `${beforeWords}`,
        after: `${afterWords}`,
        direction: directionFor(beforeWords, afterWords),
      },
      {
        label: 'WPM',
        before: `${firstAttempt.transcript.wpm}`,
        after: `${retryAttempt.transcript.wpm}`,
        direction: directionFor(firstAttempt.transcript.wpm, retryAttempt.transcript.wpm),
      },
      {
        label: '평균 평가',
        before: beforeRubric.toFixed(1),
        after: afterRubric.toFixed(1),
        direction: directionFor(beforeRubric, afterRubric),
      },
      {
        label: '긴 멈춤',
        before: `${firstAttempt.transcript.metrics.longPauses}`,
        after: `${retryAttempt.transcript.metrics.longPauses}`,
        direction: directionFor(
          retryAttempt.transcript.metrics.longPauses,
          firstAttempt.transcript.metrics.longPauses,
        ),
      },
      ...rubricMetrics,
    ],
    missionResults: missions.map((mission, index) => ({
      mission,
      achieved:
        index === 0
          ? afterRubric > beforeRubric
          : index === 1
            ? (afterScores.get('content') ?? 0) > (beforeScores.get('content') ?? 0)
            : (afterScores.get('discourse') ?? 0) >= (beforeScores.get('discourse') ?? 0),
    })),
    improvedAreas,
    remainingCoreIssue: retryAttempt.evaluation.blocker.title,
    recommendedNextQuestionType: NEXT_TYPE_BY_RUBRIC[weakestRubric],
    provider: 'local',
  }
}
