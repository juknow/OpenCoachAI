import { useEffect, useReducer, useState } from 'react'
import './App.css'
import { AppHeader } from './components/AppHeader.tsx'
import { ApiConnectionDialog } from './components/ApiConnectionDialog.tsx'
import { ProcessingScreen } from './components/ProcessingScreen.tsx'
import { getRandomQuestion } from './data/questions.ts'
import { coachService } from './services/coachProvider.ts'
import {
  loadStoredCoachState,
  saveConnection,
  saveHistory,
  saveProfile,
} from './services/storageService.ts'
import {
  coachReducer,
  createInitialCoachState,
} from './state/coachReducer.ts'
import type {
  AttemptResult,
  PracticeProfile,
  ProcessingStage,
  QuestionType,
  RecordingArtifact,
  TranscriptResult,
} from './types/coach.ts'
import { FeedbackPage } from './pages/FeedbackPage.tsx'
import { HistoryPage } from './pages/HistoryPage.tsx'
import { LandingPage } from './pages/LandingPage.tsx'
import { PracticeHomePage } from './pages/PracticeHomePage.tsx'
import { PracticePage } from './pages/PracticePage.tsx'
import { ProfileSetupPage } from './pages/ProfileSetupPage.tsx'
import { TranscriptReviewPage } from './pages/TranscriptReviewPage.tsx'

const createSessionId = () =>
  window.crypto.randomUUID?.() ?? `practice-${Date.now()}`

function App() {
  const [state, dispatch] = useReducer(
    coachReducer,
    loadStoredCoachState(),
    createInitialCoachState,
  )
  const [connectionOpen, setConnectionOpen] = useState(false)
  const [processingStage, setProcessingStage] =
    useState<ProcessingStage>('upload')
  const [operationError, setOperationError] = useState<string | null>(null)

  useEffect(() => saveProfile(state.profile), [state.profile])
  useEffect(() => saveConnection(state.connection), [state.connection])
  useEffect(() => saveHistory(state.history), [state.history])

  const goHome = () => {
    dispatch({ type: 'NAVIGATE', view: state.profile ? 'home' : 'landing' })
  }

  const startQuestion = (type?: QuestionType) => {
    if (!state.profile) {
      dispatch({ type: 'NAVIGATE', view: 'profile' })
      return
    }
    const question = getRandomQuestion(state.profile.difficulty, type)
    dispatch({ type: 'START_SESSION', id: createSessionId(), question })
  }

  const submitRecording = async (artifact: RecordingArtifact) => {
    if (!state.session) return
    setOperationError(null)
    setProcessingStage('upload')
    dispatch({ type: 'NAVIGATE', view: 'processing' })
    try {
      const transcript = await coachService.transcribe(
        {
          audio: artifact.blob,
          question: state.session.question,
          attempt: state.session.attempt,
          metrics: artifact.metrics,
        },
        setProcessingStage,
      )
      dispatch({ type: 'SET_TRANSCRIPT', transcript })
    } catch {
      setOperationError('Mock 전사 처리에 실패했습니다. 녹음을 다시 제출해 주세요.')
      dispatch({ type: 'NAVIGATE', view: 'practice' })
    }
  }

  const evaluateTranscript = async (transcript: TranscriptResult) => {
    if (!state.session || !state.profile) return
    setOperationError(null)
    setProcessingStage('evaluate')
    dispatch({ type: 'NAVIGATE', view: 'processing' })
    try {
      const evaluation = await coachService.evaluate(
        {
          question: state.session.question,
          profile: state.profile,
          transcript,
          attempt: state.session.attempt,
        },
        setProcessingStage,
      )
      const result: AttemptResult = {
        attempt: state.session.attempt,
        transcript,
        evaluation,
        completedAt: new Date().toISOString(),
      }

      if (state.session.attempt === 2 && state.session.firstAttempt) {
        const comparison = await coachService.compare({
          firstAttempt: state.session.firstAttempt,
          retryAttempt: result,
          missions: state.session.firstAttempt.evaluation.retryMission,
        })
        dispatch({ type: 'COMPLETE_ATTEMPT', result, comparison })
      } else {
        dispatch({ type: 'COMPLETE_ATTEMPT', result })
      }
    } catch {
      setOperationError('Mock 평가 처리에 실패했습니다. 전사문을 확인하고 다시 시도해 주세요.')
      dispatch({ type: 'SET_TRANSCRIPT', transcript })
    }
  }

  const renderView = () => {
    switch (state.view) {
      case 'landing':
        return (
          <LandingPage
            onStart={() =>
              dispatch({
                type: 'NAVIGATE',
                view: state.profile ? 'home' : 'profile',
              })
            }
          />
        )
      case 'profile':
        return (
          <ProfileSetupPage
            initialProfile={state.profile}
            onBack={goHome}
            onSave={(profile: PracticeProfile) =>
              dispatch({ type: 'SAVE_PROFILE', profile })
            }
          />
        )
      case 'home':
        return state.profile ? (
          <PracticeHomePage
            profile={state.profile}
            history={state.history}
            onRandom={() => startQuestion()}
            onType={startQuestion}
            onEditProfile={() => dispatch({ type: 'NAVIGATE', view: 'profile' })}
            onOpenRecord={(record) => dispatch({ type: 'OPEN_RECORD', record })}
          />
        ) : (
          <LandingPage onStart={() => dispatch({ type: 'NAVIGATE', view: 'profile' })} />
        )
      case 'practice':
        return state.session ? (
          <PracticePage
            key={`${state.session.id}-${state.session.attempt}`}
            session={state.session}
            onBack={() =>
              dispatch({
                type: 'NAVIGATE',
                view: state.session?.attempt === 2 ? 'feedback' : 'home',
              })
            }
            onSubmit={(artifact) => void submitRecording(artifact)}
          />
        ) : null
      case 'processing':
        return <ProcessingScreen stage={processingStage} />
      case 'transcript':
        return state.session ? (
          <TranscriptReviewPage
            session={state.session}
            onBack={() => dispatch({ type: 'NAVIGATE', view: 'practice' })}
            onEvaluate={(transcript) => void evaluateTranscript(transcript)}
          />
        ) : null
      case 'feedback':
        return state.session ? (
          <FeedbackPage
            session={state.session}
            onHome={goHome}
            onRetry={() => dispatch({ type: 'START_RETRY' })}
          />
        ) : null
      case 'history':
        return (
          <HistoryPage
            history={state.history}
            onStart={() => startQuestion()}
            onOpen={(record) => dispatch({ type: 'OPEN_RECORD', record })}
            onDelete={(id) => dispatch({ type: 'DELETE_RECORD', id })}
            onClear={() => dispatch({ type: 'CLEAR_HISTORY' })}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="app">
      <AppHeader
        view={state.view}
        profile={state.profile}
        connection={state.connection}
        onHome={goHome}
        onHistory={() => dispatch({ type: 'NAVIGATE', view: 'history' })}
        onConnection={() => setConnectionOpen(true)}
      />
      {operationError && (
        <div className="global-error" role="alert">
          {operationError}
          <button type="button" onClick={() => setOperationError(null)} aria-label="오류 메시지 닫기">×</button>
        </div>
      )}
      {renderView()}
      {connectionOpen && (
        <ApiConnectionDialog
          connected={state.connection.status === 'mock_connected'}
          onClose={() => setConnectionOpen(false)}
          onConnect={() => {
            dispatch({
              type: 'SET_CONNECTION',
              connection: { status: 'mock_connected' },
            })
            setConnectionOpen(false)
          }}
          onDisconnect={() => {
            dispatch({
              type: 'SET_CONNECTION',
              connection: { status: 'disconnected' },
            })
            setConnectionOpen(false)
          }}
        />
      )}
    </div>
  )
}

export default App
