import { useCallback, useEffect, useRef, useState } from 'react'
import { analyzeAudio } from '../services/audioAnalysisService.ts'
import type {
  RecordingArtifact,
  RecordingPhase,
} from '../types/coach.ts'

const MAX_RECORDING_SECONDS = 120

const chooseMimeType = () => {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
  ]
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? ''
}

const stopStream = (stream: MediaStream | null) => {
  stream?.getTracks().forEach((track) => track.stop())
}

const createPlaybackUrl = (blob: Blob): Promise<string> => {
  if (typeof URL.createObjectURL === 'function') {
    return Promise.resolve(URL.createObjectURL(blob))
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result)
        return
      }
      reject(new Error('녹음 파일의 재생 URL을 만들지 못했습니다.'))
    }
    reader.onerror = () =>
      reject(reader.error ?? new Error('녹음 파일을 읽지 못했습니다.'))
    reader.readAsDataURL(blob)
  })
}

const releasePlaybackUrl = (url: string | null) => {
  if (url?.startsWith('blob:') && typeof URL.revokeObjectURL === 'function') {
    URL.revokeObjectURL(url)
  }
}

export interface RecorderController {
  phase: RecordingPhase
  elapsedSeconds: number
  inputLevel: number
  artifact: RecordingArtifact | null
  error: string | null
  devices: MediaDeviceInfo[]
  selectedDeviceId: string
  setSelectedDeviceId: (deviceId: string) => void
  start: () => Promise<void>
  stop: () => void
  reset: () => void
}

export const useRecorder = (): RecorderController => {
  const [phase, setPhase] = useState<RecordingPhase>('idle')
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [inputLevel, setInputLevel] = useState(0)
  const [artifact, setArtifact] = useState<RecordingArtifact | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState('')

  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const startedAtRef = useRef(0)
  const timerRef = useRef<number | null>(null)
  const animationRef = useRef<number | null>(null)
  const levelContextRef = useRef<AudioContext | null>(null)
  const artifactUrlRef = useRef<string | null>(null)
  const discardRef = useRef(false)

  const refreshDevices = useCallback(async () => {
    if (!navigator.mediaDevices?.enumerateDevices) return
    try {
      const available = await navigator.mediaDevices.enumerateDevices()
      setDevices(available.filter((device) => device.kind === 'audioinput'))
    } catch {
      setDevices([])
    }
  }, [])

  const clearClock = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (animationRef.current !== null) {
      window.cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const releaseLiveAudio = useCallback(() => {
    clearClock()
    stopStream(streamRef.current)
    streamRef.current = null
    if (levelContextRef.current) {
      void levelContextRef.current.close()
      levelContextRef.current = null
    }
    setInputLevel(0)
  }, [clearClock])

  const reset = useCallback(() => {
    discardRef.current = true
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    else releaseLiveAudio()
    recorderRef.current = null
    chunksRef.current = []
    releasePlaybackUrl(artifactUrlRef.current)
    artifactUrlRef.current = null
    setArtifact(null)
    setElapsedSeconds(0)
    setError(null)
    setPhase('idle')
  }, [releaseLiveAudio])

  const stop = useCallback(() => {
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
  }, [])

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('이 브라우저에서는 음성 녹음을 지원하지 않습니다.')
      setPhase('error')
      return
    }

    discardRef.current = false
    releasePlaybackUrl(artifactUrlRef.current)
    artifactUrlRef.current = null
    setArtifact(null)
    setElapsedSeconds(0)
    setInputLevel(0)
    setError(null)
    setPhase('requesting')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: selectedDeviceId
          ? { deviceId: { exact: selectedDeviceId } }
          : true,
      })
      streamRef.current = stream
      await refreshDevices()

      const mimeType = chooseMimeType()
      if (!mimeType) {
        stopStream(stream)
        streamRef.current = null
        setError('이 브라우저에서는 지원되는 녹음 파일 형식을 만들 수 없습니다.')
        setPhase('error')
        return
      }
      const recorder = new MediaRecorder(
        stream,
        { mimeType, audioBitsPerSecond: 48_000 },
      )
      recorderRef.current = recorder
      chunksRef.current = []
      startedAtRef.current = Date.now()

      const levelContext = new AudioContext()
      levelContextRef.current = levelContext
      const source = levelContext.createMediaStreamSource(stream)
      const analyser = levelContext.createAnalyser()
      analyser.fftSize = 512
      source.connect(analyser)
      const frequencyData = new Uint8Array(analyser.frequencyBinCount)
      const readLevel = () => {
        analyser.getByteFrequencyData(frequencyData)
        const average =
          frequencyData.reduce((total, value) => total + value, 0) /
          Math.max(1, frequencyData.length)
        setInputLevel(Math.min(100, Math.round(average * 1.8)))
        animationRef.current = window.requestAnimationFrame(readLevel)
      }

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onerror = () => {
        releaseLiveAudio()
        setError('녹음 중 오류가 발생했습니다. 마이크를 다시 선택해 주세요.')
        setPhase('error')
      }
      recorder.onstop = () => {
        const durationSeconds = Math.min(
          MAX_RECORDING_SECONDS,
          Math.max(0, (Date.now() - startedAtRef.current) / 1000),
        )
        const recordedBlob = new Blob(chunksRef.current, {
          type: recorder.mimeType || mimeType || 'audio/webm',
        })
        releaseLiveAudio()

        if (discardRef.current) {
          discardRef.current = false
          setPhase('idle')
          return
        }

        void Promise.all([
          analyzeAudio(recordedBlob, durationSeconds),
          createPlaybackUrl(recordedBlob),
        ]).then(([metrics, url]) => {
          artifactUrlRef.current = url
          setArtifact({
            blob: recordedBlob,
            url,
            durationSeconds,
            mimeType: recordedBlob.type,
            metrics,
          })
          setElapsedSeconds(durationSeconds)
          setPhase('recorded')
        })
      }

      recorder.start(250)
      setPhase('recording')
      readLevel()
      timerRef.current = window.setInterval(() => {
        const seconds = (Date.now() - startedAtRef.current) / 1000
        setElapsedSeconds(seconds)
        if (seconds >= MAX_RECORDING_SECONDS && recorder.state === 'recording') {
          recorder.stop()
        }
      }, 200)
    } catch (reason) {
      releaseLiveAudio()
      const isDenied =
        reason instanceof DOMException && reason.name === 'NotAllowedError'
      setError(
        isDenied
          ? '마이크 권한이 필요합니다. 브라우저 설정에서 권한을 허용해 주세요.'
          : '사용할 수 있는 마이크를 찾지 못했습니다.',
      )
      setPhase('error')
    }
  }, [refreshDevices, releaseLiveAudio, selectedDeviceId])

  useEffect(() => {
    void refreshDevices()
  }, [refreshDevices])

  useEffect(
    () => () => {
      discardRef.current = true
      if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
      releaseLiveAudio()
      releasePlaybackUrl(artifactUrlRef.current)
    },
    [releaseLiveAudio],
  )

  return {
    phase,
    elapsedSeconds,
    inputLevel,
    artifact,
    error,
    devices,
    selectedDeviceId,
    setSelectedDeviceId,
    start,
    stop,
    reset,
  }
}
