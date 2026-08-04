import { QUESTION_TYPE_META } from '../data/questions.ts'
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis.ts'
import type {
  ActiveSession,
  AttemptResult,
  ComparisonResult,
  ImprovementAnswer,
} from '../types/coach.ts'

interface FeedbackPageProps {
  session: ActiveSession
  higherAnswerStatus: 'idle' | 'loading' | 'success' | 'error'
  higherAnswerError?: string
  onGenerateHigher: () => void
  onHome: () => void
  onRetry: () => void
}

const TtsButton = ({ text, onSpeak }: { text: string; onSpeak: (text: string) => void }) => (
  <button className="tts-button" type="button" onClick={() => onSpeak(text)}>♩ 들어보기</button>
)

function ComparisonPanel({
  comparison,
  first,
  retry,
}: {
  comparison: ComparisonResult
  first: AttemptResult
  retry: AttemptResult
}) {
  return (
    <section className="comparison-panel">
      <span className="eyebrow purple">↶ RETRY COMPLETE</span>
      <h2>첫 답변과 재답변 비교</h2>
      <p>{comparison.summary}</p>
      <div className="comparison-levels">
        <article><small>BEFORE</small><strong>{comparison.levelBefore}</strong><p>{first.transcript.wordCount}단어 · {first.transcript.wpm} WPM</p></article>
        <span aria-hidden="true">→</span>
        <article className="after"><small>AFTER</small><strong>{comparison.levelAfter}</strong><p>{retry.transcript.wordCount}단어 · {retry.transcript.wpm} WPM</p></article>
      </div>
      <div className="comparison-metrics">
        {comparison.metrics.map((metric) => (
          <div key={metric.label}><span>{metric.label}</span><strong>{metric.before} → {metric.after}</strong><em className={metric.direction}>{metric.direction === 'up' ? '개선' : metric.direction === 'down' ? '확인 필요' : '유지'}</em></div>
        ))}
      </div>
      <div className="transcript-compare">
        <article><small>첫 답변</small><p>{first.transcript.confirmedTranscript}</p></article>
        <article><small>재답변</small><p>{retry.transcript.confirmedTranscript}</p></article>
      </div>
      {comparison.improvedAreas?.length ? (
        <p><strong>향상된 영역:</strong> {comparison.improvedAreas.join(', ')}</p>
      ) : null}
      {comparison.remainingCoreIssue ? (
        <p><strong>남은 핵심 문제:</strong> {comparison.remainingCoreIssue}</p>
      ) : null}
      {comparison.recommendedNextQuestionType ? (
        <p><strong>다음 추천 유형:</strong> {QUESTION_TYPE_META[comparison.recommendedNextQuestionType].label}</p>
      ) : null}
      <ul className="mission-checks">
        {comparison.missionResults.map((item) => <li key={item.mission} className={item.achieved ? 'achieved' : ''}>{item.achieved ? '✓' : '○'} {item.mission}</li>)}
      </ul>
    </section>
  )
}

function ImprovementCard({
  answer,
  onSpeak,
}: {
  answer: ImprovementAnswer
  onSpeak: (text: string) => void
}) {
  return (
    <article className="improvement-card">
      <header>
        <span className={`answer-label ${answer.variant}`}>{answer.variant === 'core' ? 'CORE' : 'NEXT'} · {answer.sentenceCount} SENTENCES · {answer.wordCount} WORDS</span>
        <TtsButton text={answer.text} onSpeak={onSpeak} />
      </header>
      <p>{answer.text}</p>
    </article>
  )
}

export function FeedbackPage({
  session,
  higherAnswerStatus,
  higherAnswerError,
  onGenerateHigher,
  onHome,
  onRetry,
}: FeedbackPageProps) {
  const speech = useSpeechSynthesis()
  const result = session.retryAttempt ?? session.firstAttempt
  if (!result || !session.firstAttempt) return null

  const evaluation = result.evaluation
  const transcript = result.transcript
  const meta = QUESTION_TYPE_META[session.question.type]
  const coreAnswer = evaluation.improvements.find((answer) => answer.variant === 'core')
  const higherAnswer = evaluation.improvements.find((answer) => answer.variant === 'next')

  return (
    <main className="feedback-page page-shell">
      <header className="feedback-intro">
        <span className="eyebrow success">✓ ANALYSIS COMPLETE · {evaluation.provider === 'local' ? 'LOCAL AI' : 'DEMO'}</span>
        <h1>{session.retryAttempt ? '재답변 비교 피드백' : '첫 번째 답변 피드백'}</h1>
        <p><span className={`type-badge ${meta.accent}`}>{meta.label}</span> {session.question.prompt}</p>
        <button className="button secondary" type="button" onClick={onHome}>연습 홈</button>
        <div className="disclaimer">{evaluation.safetyNotice ?? '♢ 예상 등급은 AI 기반 연습용 추정치이며 공식 OPIc 성적이 아닙니다.'}</div>
      </header>

      {session.comparison && session.retryAttempt && (
        <ComparisonPanel comparison={session.comparison} first={session.firstAttempt} retry={session.retryAttempt} />
      )}

      <section className="level-hero">
        <div className="level-block"><small>MOST LIKELY PRACTICE LEVEL</small><strong>{evaluation.estimatedLevel}</strong><span>예상 범위 {evaluation.estimatedRange}</span></div>
        <div className="level-summary"><span className="confidence">신뢰도 {evaluation.confidence}</span><h2>{evaluation.headline}</h2><p>{evaluation.summary}</p></div>
      </section>

      <div className="feedback-layout">
        <div className="feedback-main">
          <section className="feedback-section">
            <h2>♩ 대화형 발화 진단</h2>
            <div className="diagnostic-grid">
              {evaluation.diagnostics.map((item) => <article key={item.label}><header><strong>{item.label}</strong><em>{item.score}/4</em></header><p>{item.feedback}</p></article>)}
            </div>
            <div className="main-point-card"><span>MAIN POINT · {evaluation.mainPointLabel}</span><p>{evaluation.mainPointFeedback}</p><blockquote>“{transcript.confirmedTranscript.slice(0, 180)}”</blockquote></div>
            <div className="language-grid">
              <article><h3>Feeling language</h3><div className="tag-row">{evaluation.feelingLanguage.length ? evaluation.feelingLanguage.map((item) => <span key={item}>{item}</span>) : <span>표현 없음</span>}</div><p>감정과 반응을 표현하는 언어를 확인합니다.</p></article>
              <article><h3>연결어와 발화 리듬</h3><div className="tag-row">{evaluation.connectors.length ? evaluation.connectors.map((item, index) => <span key={`${item}-${index}`}>{item}</span>) : <span>연결어 없음</span>}</div><p>기능적인 연결 표현과 흐름을 확인합니다.</p></article>
            </div>
          </section>

          <section className="feedback-section">
            <h2>✣ 친구처럼 말하는 맞춤 표현</h2>
            <div className="expression-list">
              {evaluation.expressions.map((item) => <article key={item.expression}><div><small>{item.situation}</small><strong>{item.expression}</strong><p>{item.guidance}</p></div><TtsButton text={item.expression} onSpeak={speech.speak} /></article>)}
            </div>
            <p className="section-note">추임새는 억지로 넣기보다 생각을 정리하거나 감정을 드러낼 때 1~2개만 자연스럽게 사용하세요.</p>
          </section>

          <section className="feedback-section">
            <h2>▣ 내 답변에 바로 쓰는 회화 단어</h2>
            <div className="vocabulary-grid">
              {evaluation.vocabulary.map((item) => <article key={item.phrase}><header><span>{item.category}</span><TtsButton text={item.phrase} onSpeak={speech.speak} /></header><strong>{item.phrase}</strong><b>{item.meaning}</b><p>{item.guidance}</p><blockquote>{item.example}</blockquote></article>)}
            </div>
            <p className="section-note">내 답변의 주제와 표현 수준을 기준으로 고른 collocation이에요. 다음 답변에는 이 중 1~2개만 사용해 보세요.</p>
          </section>

          <section className="feedback-section">
            <h2>공식 기준 기반 연습 항목</h2>
            <div className="rubric-grid">
              {evaluation.rubrics.map((rubric) => <article key={rubric.key}><header><strong>{rubric.label}</strong><em>{rubric.score}/4</em></header><div className="score-bar"><span style={{ width: `${rubric.score * 25}%` }}></span></div><p>{rubric.feedback}</p></article>)}
            </div>
          </section>

          <section className="feedback-section strengths-section">
            <h2>Strengths</h2>
            <div className="strength-grid">{evaluation.strengths.map((item) => <article key={item.title}><h3>{item.title}</h3><p>{item.detail}</p><blockquote>“{item.evidence}”</blockquote></article>)}</div>
            <div className="blocker-card"><span>PRIMARY LEVEL BLOCKER</span><h3>{evaluation.blocker.title}</h3><p>{evaluation.blocker.detail}</p><blockquote>“{evaluation.blocker.evidence}”</blockquote></div>
            <h3 className="correction-title">Important Corrections</h3>
            <div className="correction-list">{evaluation.corrections.map((item) => <article key={item.before}><del>{item.before}</del><ins>{item.after}</ins><p>{item.reason}</p></article>)}</div>
          </section>

          <section className="feedback-section">
            <h2>답변 개선 버전</h2>
            <div className="improvement-list">
              {coreAnswer && <ImprovementCard answer={coreAnswer} onSpeak={speech.speak} />}
              {higherAnswer ? (
                <ImprovementCard answer={higherAnswer} onSpeak={speech.speak} />
              ) : (
                <article className="improvement-card lazy-improvement" aria-live="polite">
                  <span className="answer-label next">NEXT · ON DEMAND</span>
                  <h3>상위 레벨 답변은 필요할 때 생성합니다</h3>
                  <p>현재 전사문과 기본 개선 답변을 바탕으로 12~15문장의 자연스러운 상위 답변을 만듭니다.</p>
                  {higherAnswerStatus === 'error' && (
                    <p className="lazy-improvement-error" role="alert">
                      {higherAnswerError ?? '상위 레벨 답변 생성에 실패했습니다.'}
                    </p>
                  )}
                  <button
                    className="button secondary"
                    type="button"
                    onClick={onGenerateHigher}
                    disabled={higherAnswerStatus === 'loading'}
                  >
                    {higherAnswerStatus === 'loading'
                      ? '상위 답변 생성 중…'
                      : higherAnswerStatus === 'error'
                        ? '다시 생성하기'
                        : '상위 레벨 답변 생성'}
                  </button>
                </article>
              )}
            </div>
            <p className="section-note">기본 개선 답변은 10~12문장, 상위 답변은 12~15문장으로 구성하며 실제 문장 수와 단어 수를 계산해 표시합니다.</p>
          </section>
        </div>

        <aside className="feedback-aside">
          <section><h2>Speech Summary</h2><div className="speech-stats"><div><strong>{Math.round(transcript.metrics.durationSeconds)}s</strong><small>답변 시간</small></div><div><strong>{transcript.wpm}</strong><small>WPM</small></div><div><strong>{transcript.fillerCount}</strong><small>감지된 um/uh</small></div><div><strong>{transcript.serverMetrics?.acoustic.hesitationPauseCount ?? transcript.metrics.shortPauses}</strong><small>짧은 끊김</small></div><div><strong>{transcript.serverMetrics?.acoustic.longPauseCount ?? transcript.metrics.longPauses}</strong><small>긴 멈춤</small></div><div><strong>{transcript.serverMetrics?.acoustic.silenceRatio ?? transcript.metrics.silenceRatio}%</strong><small>무음 비율</small></div></div><p>전사 timestamp와 브라우저 파형을 이용한 결정론적 추정치 · 발음 점수가 아닙니다.</p><details><summary>원문 전사 보기</summary><p>{transcript.rawTranscript}</p></details></section>
          <section><h2>Reusable Structure</h2><ol>{evaluation.reusableStructure.map((item) => <li key={item}>{item}</li>)}</ol></section>
          <section className="retry-card"><span className="eyebrow purple">↶ RETRY MISSION</span><h2>이번에는 이것만 바꿔보세요</h2><ul>{evaluation.retryMission.map((item) => <li key={item}>✓ {item}</li>)}</ul><button className="button primary" type="button" onClick={onRetry}>같은 문제 다시 답하기 →</button></section>
        </aside>
      </div>
    </main>
  )
}
