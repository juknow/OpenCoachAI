import { QUESTION_TYPE_META } from '../data/questions.ts'
import { useRecorder } from '../hooks/useRecorder.ts'
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis.ts'
import type { ActiveSession, RecordingArtifact } from '../types/coach.ts'
import { RecorderPanel } from '../components/RecorderPanel.tsx'

interface PracticePageProps {
  session: ActiveSession
  onBack: () => void
  onSubmit: (artifact: RecordingArtifact) => void
}

export function PracticePage({ session, onBack, onSubmit }: PracticePageProps) {
  const recorder = useRecorder()
  const speech = useSpeechSynthesis()
  const meta = QUESTION_TYPE_META[session.question.type]
  const retryMission = session.firstAttempt?.evaluation.retryMission ?? []

  return (
    <main className="practice-page page-shell">
      <button className="back-button" type="button" onClick={onBack}>← {session.attempt === 2 ? '피드백으로' : '연습 홈으로'}</button>
      <div className="stepper" aria-label="연습 진행 단계">
        <span className="done">✓ 문제</span><i></i><span className="active">{session.attempt} 답변</span><i></i><span>3 피드백</span>{session.attempt === 2 && <><i></i><span>4 비교</span></>}
      </div>

      {session.attempt === 2 && (
        <section className="retry-brief">
          <span className="eyebrow purple">↶ RETRY</span>
          <h2>이번에는 이 3가지를 꼭 넣어보세요</h2>
          <ul>{retryMission.map((mission) => <li key={mission}>✓ {mission}</li>)}</ul>
          <details><summary>첫 답변의 핵심 문제 보기</summary><p>{session.firstAttempt?.evaluation.blocker.detail}</p></details>
        </section>
      )}

      <section className="question-card">
        <div className="question-meta"><span className={`type-badge ${meta.accent}`}>{meta.label.toUpperCase()}</span><span>{session.question.topic} · {session.question.difficulty}</span></div>
        <h1>{session.question.prompt}</h1>
        <div className="question-actions">
          <button className="button secondary" type="button" onClick={() => speech.speak(session.question.prompt)}>♩ {speech.speaking ? '재생 중' : '질문 음성 듣기'}</button>
          <details><summary>한국어 해석 보기</summary><p>{session.question.translation}</p></details>
        </div>
        <small>질문 음성은 브라우저의 무료 영어 음성을 사용합니다.</small>
      </section>

      <RecorderPanel recorder={recorder} onSubmit={() => recorder.artifact && onSubmit(recorder.artifact)} />
    </main>
  )
}
