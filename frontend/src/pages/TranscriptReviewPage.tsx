import { useMemo, useState } from 'react'
import { updateTranscriptText } from '../services/mockCoachService.ts'
import type { ActiveSession, TranscriptResult } from '../types/coach.ts'

interface TranscriptReviewPageProps {
  session: ActiveSession
  onBack: () => void
  onEvaluate: (transcript: TranscriptResult) => void
}

export function TranscriptReviewPage({
  session,
  onBack,
  onEvaluate,
}: TranscriptReviewPageProps) {
  const transcript = session.transcript
  const [editedText, setEditedText] = useState(transcript?.editedText ?? '')
  const editedTranscript = useMemo(
    () => (transcript ? updateTranscriptText(transcript, editedText) : null),
    [editedText, transcript],
  )

  if (!editedTranscript) return null

  return (
    <main className="transcript-page page-shell">
      <button className="back-button" type="button" onClick={onBack}>← 다시 녹음하기</button>
      <header className="page-intro centered">
        <span className="eyebrow">MOCK TRANSCRIPT CHECK</span>
        <h1>전사문을 확인해 주세요</h1>
        <p>음성 인식이 잘못된 부분만 고쳐 주세요. 수정된 텍스트를 기준으로 평가합니다.</p>
      </header>

      <section className="transcript-card">
        <div className="transcript-question">♧ {session.question.prompt}</div>
        <label htmlFor="transcript-text">영어 전사문 · 원문 그대로</label>
        <textarea
          id="transcript-text"
          value={editedText}
          onChange={(event) => setEditedText(event.target.value)}
          rows={10}
        />
        <div className="metric-chips">
          <span>◷ {Math.round(editedTranscript.metrics.durationSeconds)}초</span>
          <span>▤ {editedTranscript.wordCount}단어</span>
          <span>ϟ {editedTranscript.wpm} WPM</span>
          <span>♩ um/uh {editedTranscript.fillerCount}회</span>
          <span>♩ 짧은 끊김 {editedTranscript.metrics.shortPauses}회</span>
          <span>♩ 긴 멈춤 {editedTranscript.metrics.longPauses}회</span>
        </div>
        <p className="transcript-note">
          Mock 전사는 um/uh, 반복한 단어, 중간에 끊긴 문장, 잘못된 문법과 어휘도
          그대로 포함합니다. 음성 흐름 지표는 실제 녹음 파형에서 별도로 추정합니다.
        </p>
        <div className="card-actions">
          <button className="button secondary" type="button" onClick={onBack}>다시 녹음</button>
          <button className="button primary" type="button" disabled={!editedText.trim()} onClick={() => onEvaluate(editedTranscript)}>Mock AI 피드백 받기 ✣</button>
        </div>
      </section>
    </main>
  )
}

