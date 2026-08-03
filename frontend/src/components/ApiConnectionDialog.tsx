import { useEffect } from 'react'
import type { ConnectionState } from '../types/coach.ts'

interface ApiConnectionDialogProps {
  connection: ConnectionState
  onClose: () => void
  onUseApi: () => void
  onUseDemo: () => void
  onRefresh: () => void
}

export function ApiConnectionDialog({
  connection,
  onClose,
  onUseApi,
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
  const usingApi = connection.provider === 'openai'
  const statusText =
    connection.backendStatus === 'checking'
      ? '백엔드 연결 상태를 확인하고 있습니다.'
      : apiReady
        ? '백엔드에 API 키가 설정되어 실제 API Mode를 사용할 수 있습니다.'
        : connection.backendStatus === 'unconfigured'
          ? '백엔드에 API 키가 없어 Demo Mode를 사용합니다.'
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
        <span className="eyebrow">{usingApi ? 'OPENAI API MODE' : 'DEMO MODE'}</span>
        <h2 id="connection-title">전사와 피드백 연결</h2>
        <p>
          {statusText} API 키는 서버의 <code>backend/.env</code>에서만 읽으며
          브라우저에는 입력하거나 저장하지 않습니다.
        </p>

        <label className="check-row">
          <input type="checkbox" checked readOnly />
          현재 provider: {usingApi ? 'OpenAI API' : 'Demo mock'}
        </label>
        <p className="secure-note">
          연결 해제는 키를 삭제하지 않고 이 브라우저의 provider만 Demo Mode로
          전환합니다. localStorage에는 provider 선호만 저장됩니다.
        </p>

        <div className="dialog-actions">
          <button className="button secondary" type="button" onClick={onRefresh}>상태 새로 확인</button>
          <button
            className="button primary"
            type="button"
            disabled={!usingApi && !apiReady}
            onClick={usingApi ? onUseDemo : onUseApi}
          >
            {usingApi ? '연결 해제 · Demo Mode' : '실제 API Mode 사용'}
          </button>
        </div>
      </section>
    </div>
  )
}
