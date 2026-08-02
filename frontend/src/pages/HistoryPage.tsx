import { QUESTION_TYPE_META } from '../data/questions.ts'
import type { PracticeRecord } from '../types/coach.ts'

interface HistoryPageProps {
  history: PracticeRecord[]
  onStart: () => void
  onOpen: (record: PracticeRecord) => void
  onDelete: (id: string) => void
  onClear: () => void
}

export function HistoryPage({ history, onStart, onOpen, onDelete, onClear }: HistoryPageProps) {
  const confirmClear = () => {
    if (window.confirm('저장된 모든 연습 기록을 삭제할까요?')) onClear()
  }

  return (
    <main className="history-page page-shell">
      <header className="history-intro">
        <div><span className="eyebrow">PRACTICE LOG</span><h1>연습 기록</h1><p>답변, 피드백, 재답변 비교 결과는 이 브라우저에만 저장됩니다.</p></div>
        {history.length > 0 && <button className="button delete-outline" type="button" onClick={confirmClear}>♧ 전체 삭제</button>}
      </header>

      {history.length === 0 ? (
        <section className="history-empty"><span aria-hidden="true">↶</span><h2>저장된 연습이 없어요</h2><p>문제 하나를 완료하면 이곳에서 피드백을 다시 볼 수 있습니다.</p><button className="button primary" type="button" onClick={onStart}>첫 연습 시작하기</button></section>
      ) : (
        <div className="history-list">
          {history.map((record) => {
            const level = record.retryAttempt?.evaluation.estimatedLevel ?? record.firstAttempt.evaluation.estimatedLevel
            return (
              <article key={record.id}>
                <button className="history-open" type="button" onClick={() => onOpen(record)}>
                  <span className="history-mic">♩</span>
                  <span className="history-copy"><span><em>{QUESTION_TYPE_META[record.question.type].label}</em><small>{new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(record.createdAt))}</small></span><strong>{record.question.prompt}</strong><small>{record.retryAttempt ? '재답변 비교 완료' : '첫 번째 피드백 완료'} · {record.firstAttempt.transcript.wordCount}단어</small></span>
                  <span className="history-level"><small>연습 등급</small><strong>{level}</strong>→</span>
                </button>
                <button className="record-delete" type="button" aria-label="이 기록 삭제" onClick={() => { if (window.confirm('이 연습 기록을 삭제할까요?')) onDelete(record.id) }}>♧</button>
              </article>
            )
          })}
        </div>
      )}
      <p className="storage-note">♢ 원본 오디오는 저장하지 않습니다. 전사문과 평가 결과만 이 브라우저에 저장됩니다.</p>
    </main>
  )
}

