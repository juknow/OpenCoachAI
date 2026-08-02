interface LandingPageProps {
  onStart: () => void
}

export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <main className="landing-page">
      <section className="landing-hero">
        <div className="hero-copy">
          <span className="hero-kicker">✣ 말하고, 피드백 받고, 다시 말해보세요</span>
          <h1>
            당신의 영어 답변을
            <strong>한 단계 더 높게.</strong>
          </h1>
          <p>
            OPIc 스타일 질문에 직접 답하고, 답변의 강점과 핵심 약점을 분석해
            다음 답변을 더 좋아지게 만들어 드려요.
          </p>
          <button className="button hero-button" type="button" onClick={onStart}>
            연습 시작하기 <span aria-hidden="true">→</span>
          </button>
          <div className="disclaimer compact">♢ 예상 등급은 AI 기반 연습용 추정치이며 공식 OPIc 성적이 아닙니다.</div>
        </div>

        <div className="feedback-preview" aria-label="OPIc AI Coach 피드백 화면 미리보기">
          <div className="preview-window-bar"><span></span> Practice feedback</div>
          <div className="preview-question">
            <span className="type-badge blue">PAST EXPERIENCE</span>
            <strong>Tell me about a memorable trip.</strong>
          </div>
          <div className="preview-stats">
            <div><small>예상 범위</small><strong>IM2 ~ IH</strong></div>
            <div><small>신뢰도</small><strong>보통</strong></div>
            <div><small>WPM</small><strong>102</strong></div>
          </div>
          <div className="preview-bars"><span></span><span></span><span></span><span></span></div>
          <div className="preview-blocker">
            <small>PRIMARY LEVEL BLOCKER</small>
            <strong>사건의 순서와 결과를 더 구체적으로 연결해 보세요.</strong>
          </div>
        </div>
      </section>

      <section className="feature-strip" aria-label="주요 기능">
        <article><span>♩</span><div><strong>말하기</strong><p>브라우저에서 바로 녹음</p></div></article>
        <article><span>▥</span><div><strong>분석하기</strong><p>대화 흐름·Main Point·발화 리듬 진단</p></div></article>
        <article><span>↶</span><div><strong>다시 말하기</strong><p>Retry Mission으로 즉시 개선</p></div></article>
      </section>
    </main>
  )
}

