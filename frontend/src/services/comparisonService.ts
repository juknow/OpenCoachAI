import type {
  AttemptResult,
  ComparisonMetric,
  ComparisonResult,
} from '../types/coach.ts'

const averageRubric = (attempt: AttemptResult) =>
  attempt.evaluation.rubrics.reduce((total, rubric) => total + rubric.score, 0) /
  Math.max(1, attempt.evaluation.rubrics.length)

const directionFor = (before: number, after: number): ComparisonMetric['direction'] =>
  after > before ? 'up' : after < before ? 'down' : 'same'

export const compareAttempts = (
  firstAttempt: AttemptResult,
  retryAttempt: AttemptResult,
  missions: string[],
): ComparisonResult => {
  const beforeWords = firstAttempt.transcript.wordCount
  const afterWords = retryAttempt.transcript.wordCount
  const beforeRubric = averageRubric(firstAttempt)
  const afterRubric = averageRubric(retryAttempt)

  return {
    levelBefore: firstAttempt.evaluation.estimatedLevel,
    levelAfter: retryAttempt.evaluation.estimatedLevel,
    summary:
      afterWords > beforeWords
        ? '재답변에서 발화량과 구조가 개선되었습니다. 다음에는 구체적인 예를 한 가지 더 추가해 보세요.'
        : '핵심 구조는 유지되었지만 발화량 변화가 크지 않습니다. Retry Mission을 하나씩 다시 적용해 보세요.',
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
    ],
    missionResults: missions.map((mission, index) => ({
      mission,
      achieved: index === 0 ? afterWords >= beforeWords : afterWords > beforeWords,
    })),
    provider: 'local',
  }
}
