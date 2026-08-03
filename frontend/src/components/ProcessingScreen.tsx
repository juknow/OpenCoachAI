import type { CoachProvider, ProcessingStage } from '../types/coach.ts'

interface ProcessingScreenProps {
  stage: ProcessingStage
  provider: CoachProvider
}

export function ProcessingScreen({ stage, provider }: ProcessingScreenProps) {
  const modeLabel = provider === 'openai' ? 'OpenAI' : 'Demo'
  const stages: Array<{ key: ProcessingStage; label: string }> = [
    { key: 'upload', label: '음성을 안전하게 준비하고 있습니다' },
    { key: 'transcribe', label: `${modeLabel} 영어 전사문을 만들고 있습니다` },
    { key: 'evaluate', label: `답변 내용을 ${modeLabel} 평가하고 있습니다` },
    { key: 'improve', label: '맞춤형 개선안을 만들고 있습니다' },
  ]
  const activeIndex = stages.findIndex((item) => item.key === stage)

  return (
    <main className="processing-page">
      <section className="processing-card" aria-live="polite">
        <div className="coach-spinner" aria-hidden="true"></div>
        <span className="eyebrow purple">{modeLabel.toUpperCase()} AI COACH</span>
        <h1>답변을 꼼꼼히 살펴보고 있어요</h1>
        <p>잠시만 기다려 주세요. 전사문은 이 과정에서 사라지지 않습니다.</p>
        <ol className="processing-list">
          {stages.map((item, index) => (
            <li key={item.key} className={index < activeIndex ? 'done' : index === activeIndex ? 'active' : ''}>
              <span>{index < activeIndex ? '✓' : index + 1}</span>
              {item.label}
            </li>
          ))}
        </ol>
      </section>
    </main>
  )
}
