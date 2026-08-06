import type { RecorderController } from '../hooks/useRecorder.ts'
import { isEffectivelySilent } from '../services/audioAnalysisService.ts'

const formatTime = (seconds: number) => {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safeSeconds / 60)
  return `${String(minutes).padStart(2, '0')}:${String(safeSeconds % 60).padStart(2, '0')}`
}

interface RecorderPanelProps {
  recorder: RecorderController
  onSubmit: () => void
}

export function RecorderPanel({ recorder, onSubmit }: RecorderPanelProps) {
  const effectivelySilent = recorder.artifact
    ? isEffectivelySilent(recorder.artifact.metrics)
    : false
  const canSubmit =
    recorder.phase === 'recorded' &&
    Boolean(recorder.artifact) &&
    !effectivelySilent

  return (
    <section className="answer-card">
      <div className="section-heading-row">
        <div>
          <span className="section-icon" aria-hidden="true">♩</span>
          <div>
            <h2>답변 녹음</h2>
            <p>말하는 동안 입력을 추적하고, 종료 후 속도·멈춤 변화를 분석해요.</p>
          </div>
        </div>
        <span className="time-limit">최대 2분</span>
      </div>

      <div className={`recorder-stage ${recorder.phase}`} aria-live="polite">
        {recorder.phase === 'idle' || recorder.phase === 'error' ? (
          <>
            <div className="mic-orb" aria-hidden="true">♩</div>
            <label className="device-field">
              <span>입력 마이크</span>
              <select
                value={recorder.selectedDeviceId}
                onChange={(event) => recorder.setSelectedDeviceId(event.target.value)}
              >
                <option value="">시스템 기본 마이크</option>
                {recorder.devices.map((device, index) => (
                  <option key={device.deviceId || `device-${index}`} value={device.deviceId}>
                    {device.label || `마이크 ${index + 1}`}
                  </option>
                ))}
              </select>
            </label>
            <strong>준비가 되면 녹음을 시작하세요</strong>
            <small>짧은 답변도 가능 · 최대 2분</small>
            <div className="recording-time" aria-label={`녹음 시간 ${formatTime(recorder.elapsedSeconds)}`}>
              {formatTime(recorder.elapsedSeconds)}
            </div>
            {recorder.error && <p className="recorder-error">{recorder.error}</p>}
            <button className="button primary record-button" type="button" onClick={() => void recorder.start()}>
              ♩ 녹음 시작
            </button>
          </>
        ) : recorder.phase === 'requesting' ? (
          <>
            <div className="mic-orb loading" aria-hidden="true">♩</div>
            <strong>마이크를 연결하고 있어요</strong>
            <small>브라우저 권한 요청을 확인해 주세요.</small>
            <div className="recording-time">00:00</div>
            <button className="button primary" type="button" disabled>마이크 연결 중</button>
          </>
        ) : recorder.phase === 'recording' ? (
          <>
            <div className="mic-orb active" aria-hidden="true">♩</div>
            <strong>답변을 녹음하고 있어요</strong>
            <small>마이크 입력 {recorder.inputLevel}% · 원하는 때 종료하세요</small>
            <div className="recording-time">{formatTime(recorder.elapsedSeconds)}</div>
            <div className="input-meter" aria-label={`마이크 입력 수준 ${recorder.inputLevel}%`}>
              <span style={{ width: `${Math.max(2, recorder.inputLevel)}%` }}></span>
            </div>
            <button className="button danger" type="button" onClick={recorder.stop}>■ 녹음 종료</button>
          </>
        ) : (
          <>
            <div className="mic-orb" aria-hidden="true">♩</div>
            <strong>답변 녹음 완료</strong>
            <small>재생해서 실제 목소리가 들리는지 확인한 뒤 제출해 주세요.</small>
            <div className="recording-time">{formatTime(recorder.elapsedSeconds)}</div>
            {recorder.artifact && (
              <audio className="audio-preview" controls src={recorder.artifact.url} aria-label="녹음 미리 듣기" />
            )}
            {effectivelySilent && (
              <p className="recorder-error">목소리가 감지되지 않았습니다. 마이크를 확인하고 다시 녹음해 주세요.</p>
            )}
            <button className="button secondary" type="button" onClick={recorder.reset}>↶ 다시 녹음</button>
          </>
        )}
      </div>

      <button className="button submit-button" type="button" disabled={!canSubmit} onClick={onSubmit}>
        답변 제출하고 음성 전사하기 <span aria-hidden="true">→</span>
      </button>
    </section>
  )
}
