import { QUESTION_TYPE_META } from '../data/questions.ts'
import type { PracticeProfile, PracticeRecord, QuestionType } from '../types/coach.ts'

interface PracticeHomePageProps {
  profile: PracticeProfile
  history: PracticeRecord[]
  onRandom: () => void
  onType: (type: QuestionType) => void
  onEditProfile: () => void
  onOpenRecord: (record: PracticeRecord) => void
}

export function PracticeHomePage({
  profile,
  history,
  onRandom,
  onType,
  onEditProfile,
  onOpenRecord,
}: PracticeHomePageProps) {
  const retryCount = history.filter((record) => record.retryAttempt).length
  const recentLevel = history[0]?.retryAttempt?.evaluation.estimatedLevel ?? history[0]?.firstAttempt.evaluation.estimatedLevel ?? '—'

  return (
    <main className="practice-home page-shell">
      <section className="today-card">
        <span className="eyebrow inverted">TODAY&apos;S PRACTICE</span>
        <h1>오늘도 한 번,<br />더 나은 답변을 만들어볼까요?</h1>
        <p>새롭게 구성한 150개의 OPIc 스타일 질문 중 선택한 난이도에 맞춰 랜덤으로 출제해요.</p>
        <button className="button white" type="button" onClick={onRandom}>▶ 랜덤 문제 시작</button>
      </section>

      <section className="home-summary">
        <article><span>▣</span><strong>{history.length}</strong><small>누적 연습</small></article>
        <article><span>↶</span><strong>{retryCount}</strong><small>재답변 완료</small></article>
        <article><span>⌁</span><strong>{recentLevel}</strong><small>최근 연습 등급</small></article>
        <article className="profile-summary"><small>목표 등급</small><strong>{profile.targetLevel}</strong><button type="button" onClick={onEditProfile}>프로필 수정</button></article>
      </section>

      <section className="type-section">
        <header><div><h2>유형별 연습</h2><p>각 유형마다 Easy 9 · Medium 8 · Hard 8문항으로 구성했습니다.</p></div></header>
        <div className="type-grid">
          {(Object.entries(QUESTION_TYPE_META) as Array<[QuestionType, (typeof QUESTION_TYPE_META)[QuestionType]]>).map(([type, meta]) => (
            <button key={type} className={`type-card accent-${meta.accent}`} type="button" onClick={() => onType(type)}>
              <span className="type-card-icon" aria-hidden="true">☷</span>
              <strong>{meta.label}</strong>
              <p>{meta.description}</p>
              <em>문제 25개 →</em>
            </button>
          ))}
        </div>
      </section>

      <section className="recent-section">
        <h2>최근 연습</h2>
        <p>최근 답변과 개선 결과를 다시 확인해 보세요.</p>
        {history.length === 0 ? (
          <div className="empty-inline"><strong>아직 연습 기록이 없어요</strong><span>첫 번째 문제에 답하면 결과가 여기에 쌓입니다.</span></div>
        ) : (
          <div className="recent-list">
            {history.slice(0, 3).map((record) => (
              <button key={record.id} type="button" onClick={() => onOpenRecord(record)}>
                <span className="type-badge blue">{QUESTION_TYPE_META[record.question.type].label}</span>
                <strong>{record.question.prompt}</strong>
                <em>{record.retryAttempt ? '재답변 비교 완료' : '첫 번째 피드백 완료'} · {record.firstAttempt.evaluation.estimatedLevel}</em>
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
