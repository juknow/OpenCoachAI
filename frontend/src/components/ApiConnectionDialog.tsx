import { useEffect, useState } from 'react'

interface ApiConnectionDialogProps {
  connected: boolean
  onClose: () => void
  onConnect: () => void
  onDisconnect: () => void
}

export function ApiConnectionDialog({
  connected,
  onClose,
  onConnect,
  onDisconnect,
}: ApiConnectionDialogProps) {
  const [keyDraft, setKeyDraft] = useState('')

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const handleConnect = () => {
    onConnect()
    setKeyDraft('')
  }

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
        <span className="eyebrow">MOCK AI MODE</span>
        <h2 id="connection-title">전사와 피드백 연결</h2>
        <p>
          이번 이식 단계에서는 실제 API를 호출하지 않습니다. 입력값은 어떤 서버에도
          전송되지 않으며 브라우저에도 저장되지 않습니다.
        </p>

        <label className="field-label" htmlFor="mock-key">OpenAI API 키 형식 · Mock</label>
        <input
          id="mock-key"
          type="password"
          value={keyDraft}
          onChange={(event) => setKeyDraft(event.target.value)}
          placeholder="sk-... (저장·전송되지 않음)"
          autoComplete="off"
        />
        <label className="check-row">
          <input type="checkbox" checked readOnly />
          이 브라우저에서 Mock 연결 상태 유지
        </label>
        <p className="secure-note">
          실제 키 대신 아무 테스트 문자열을 입력해도 됩니다. localStorage에는
          <code>mock_connected</code> 상태만 저장합니다.
        </p>

        <div className="dialog-actions">
          {connected && (
            <button className="button secondary" type="button" onClick={onDisconnect}>연결 해제</button>
          )}
          <button
            className="button primary"
            type="button"
            disabled={!connected && keyDraft.trim().length < 3}
            onClick={handleConnect}
          >
            {connected ? '연결 상태 갱신' : 'Mock 연결하고 계속'}
          </button>
        </div>
      </section>
    </div>
  )
}

