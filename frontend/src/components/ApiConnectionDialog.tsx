import { useEffect } from 'react'
import type { ConnectionState } from '../types/coach.ts'

interface ApiConnectionDialogProps {
  connection: ConnectionState
  onClose: () => void
  onUseLocal: () => void
  onUseDemo: () => void
  onRefresh: () => void
}

export function ApiConnectionDialog({
  connection,
  onClose,
  onUseLocal,
  onUseDemo,
  onRefresh,
}: ApiConnectionDialogProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const apiReady = connection.backendStatus === 'ready'
  const usingLocal = connection.provider === 'local'
  const issueLabels: Record<string, string> = {
    OLLAMA_UNAVAILABLE: 'Ollama가 실행 중이지 않습니다.',
    OLLAMA_MODEL_UNAVAILABLE: '설정한 Ollama 모델이 설치되어 있지 않습니다.',
    WHISPER_NOT_INSTALLED: 'faster-whisper가 설치되어 있지 않습니다.',
    WHISPER_MODEL_UNAVAILABLE: '설정한 Whisper 모델을 로컬에서 찾지 못했습니다.',
    LOCAL_PROVIDER_UNAVAILABLE: '로컬 provider를 준비하지 못했습니다.',
  }
  const statusText =
    connection.backendStatus === 'checking'
      ? '백엔드 연결 상태를 확인하고 있습니다.'
      : apiReady
        ? 'Ollama와 faster-whisper가 준비되어 Local AI Mode를 사용할 수 있습니다.'
        : connection.backendStatus === 'unconfigured'
          ? '로컬 모델 준비가 완료되지 않아 Demo Mode를 사용합니다.'
          : '백엔드에 연결할 수 없어 Demo Mode를 사용합니다.'

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="connection-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="connection-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button className="dialog-close" type="button" onClick={onClose} aria-label="AI 연결 창 닫기">×</button>
        <div className="dialog-icon" aria-hidden="true">⚿</div>
        <span className="eyebrow">{usingLocal ? 'LOCAL AI MODE' : 'DEMO MODE'}</span>
        <h2 id="connection-title">전사와 피드백 연결</h2>
        <p>
          {statusText} 브라우저는 Ollama나 faster-whisper를 직접 호출하지 않고
          FastAPI 백엔드만 호출합니다.
        </p>

        {connection.readinessIssues?.length ? (
          <ul className="readiness-list">
            {connection.readinessIssues.map((issue) => (
              <li key={issue}>{issueLabels[issue] ?? issue}</li>
            ))}
          </ul>
        ) : null}

        <label className="check-row">
          <input type="checkbox" checked readOnly />
          현재 provider: {usingLocal ? 'Ollama + faster-whisper' : 'Demo mock'}
        </label>
        <p className="secure-note">
          연결 해제는 로컬 서비스를 종료하지 않고 이 브라우저의 provider만 Demo
          Mode로 전환합니다. localStorage에는 provider 선호만 저장됩니다.
        </p>

        <div className="dialog-actions">
          <button className="button secondary" type="button" onClick={onRefresh}>상태 새로 확인</button>
          <button
            className="button primary"
            type="button"
            disabled={!usingLocal && !apiReady}
            onClick={usingLocal ? onUseDemo : onUseLocal}
          >
            {usingLocal ? '연결 해제 · Demo Mode' : 'Local AI Mode 사용'}
          </button>
        </div>
      </section>
    </div>
  )
}
