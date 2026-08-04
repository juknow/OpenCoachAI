import type {
  AppView,
  ConnectionState,
  PracticeProfile,
} from '../types/coach.ts'

interface AppHeaderProps {
  view: AppView
  profile: PracticeProfile | null
  connection: ConnectionState
  onHome: () => void
  onHistory: () => void
  onConnection: () => void
}

export function AppHeader({
  view,
  profile,
  connection,
  onHome,
  onHistory,
  onConnection,
}: AppHeaderProps) {
  const connected = connection.provider === 'local'
  const connectionLabel =
    connection.backendStatus === 'checking'
      ? '연결 확인 중'
      : connected
        ? 'Local AI Mode'
        : 'Demo Mode'

  return (
    <header className="app-header">
      <button className="brand" type="button" onClick={onHome} aria-label="OPIc AI Coach 홈">
        <span className="brand-mark" aria-hidden="true">
          <span></span><span></span><span></span>
        </span>
        <span>OPIc <strong>AI Coach</strong></span>
      </button>

      {profile && (
        <nav className="main-nav" aria-label="주요 메뉴">
          <button className={view === 'home' ? 'active' : ''} type="button" onClick={onHome}>
            <span aria-hidden="true">⌂</span> 홈
          </button>
          <button className={view === 'history' ? 'active' : ''} type="button" onClick={onHistory}>
            <span aria-hidden="true">↶</span> 기록
          </button>
        </nav>
      )}

      <div className="header-actions">
        <button
          className={`connection-pill ${connected ? 'connected' : ''}`}
          type="button"
          onClick={onConnection}
        >
          <span aria-hidden="true">⚿</span>
          {connectionLabel}
        </button>
        {profile && <span className="target-level">◎ 목표 {profile.targetLevel}</span>}
      </div>
    </header>
  )
}
