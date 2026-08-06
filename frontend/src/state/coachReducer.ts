import type {
  ActiveSession,
  AppView,
  AttemptResult,
  CoachState,
  ComparisonResult,
  ConnectionState,
  ImprovementAnswer,
  PracticeProfile,
  PracticeRecord,
  Question,
  TranscriptResult,
} from '../types/coach.ts'
import type { StoredCoachState } from '../services/storageService.ts'

export type CoachAction =
  | { type: 'NAVIGATE'; view: AppView }
  | { type: 'SAVE_PROFILE'; profile: PracticeProfile }
  | { type: 'SET_CONNECTION'; connection: ConnectionState }
  | { type: 'START_SESSION'; id: string; question: Question }
  | { type: 'SET_TRANSCRIPT'; transcript: TranscriptResult }
  | { type: 'COMPLETE_ATTEMPT'; result: AttemptResult; comparison?: ComparisonResult }
  | { type: 'SET_HIGHER_IMPROVEMENT'; attempt: 1 | 2; answer: ImprovementAnswer }
  | { type: 'START_RETRY' }
  | { type: 'OPEN_RECORD'; record: PracticeRecord }
  | { type: 'DELETE_RECORD'; id: string }
  | { type: 'CLEAR_HISTORY' }

export const createInitialCoachState = (stored: StoredCoachState): CoachState => ({
  view: stored.profile ? 'home' : 'landing',
  profile: stored.profile,
  connection: stored.connection,
  history: stored.history,
  session: null,
})

const updateSession = (
  session: ActiveSession | null,
  update: Partial<ActiveSession>,
) => (session ? { ...session, ...update } : session)

const withHigherImprovement = (
  attempt: AttemptResult | undefined,
  answer: ImprovementAnswer,
) =>
  attempt
    ? {
        ...attempt,
        evaluation: {
          ...attempt.evaluation,
          improvements: [
            ...attempt.evaluation.improvements.filter((item) => item.variant !== 'next'),
            answer,
          ],
        },
      }
    : attempt

export const coachReducer = (
  state: CoachState,
  action: CoachAction,
): CoachState => {
  switch (action.type) {
    case 'NAVIGATE':
      return {
        ...state,
        view: action.view,
        session:
          action.view === 'home' || action.view === 'landing'
            ? null
            : state.session,
      }
    case 'SAVE_PROFILE':
      return { ...state, profile: action.profile, view: 'home' }
    case 'SET_CONNECTION':
      return { ...state, connection: action.connection }
    case 'START_SESSION':
      return {
        ...state,
        view: 'practice',
        session: {
          id: action.id,
          question: action.question,
          profileSnapshot: state.profile ?? undefined,
          attempt: 1,
        },
      }
    case 'SET_TRANSCRIPT':
      return {
        ...state,
        view: 'transcript',
        session: updateSession(state.session, { transcript: action.transcript }),
      }
    case 'COMPLETE_ATTEMPT': {
      if (!state.session || !state.profile) return state

      if (action.result.attempt === 1) {
        const record: PracticeRecord = {
          id: state.session.id,
          question: state.session.question,
          profileSnapshot: state.profile,
          firstAttempt: action.result,
          createdAt: action.result.completedAt,
        }
        return {
          ...state,
          view: 'feedback',
          history: [record, ...state.history.filter((item) => item.id !== record.id)],
          session: updateSession(state.session, {
            firstAttempt: action.result,
            transcript: action.result.transcript,
          }),
        }
      }

      const comparison = action.comparison
      return {
        ...state,
        view: 'feedback',
        history: state.history.map((record) =>
          record.id === state.session?.id
            ? { ...record, retryAttempt: action.result, comparison }
            : record,
        ),
        session: updateSession(state.session, {
          retryAttempt: action.result,
          comparison,
          transcript: action.result.transcript,
        }),
      }
    }
    case 'START_RETRY':
      if (!state.session?.firstAttempt) return state
      return {
        ...state,
        view: 'practice',
        session: {
          ...state.session,
          attempt: 2,
          transcript: undefined,
          retryAttempt: undefined,
          comparison: undefined,
        },
      }
    case 'SET_HIGHER_IMPROVEMENT': {
      if (!state.session) return state
      const firstAttempt =
        action.attempt === 1
          ? withHigherImprovement(state.session.firstAttempt, action.answer)
          : state.session.firstAttempt
      const retryAttempt =
        action.attempt === 2
          ? withHigherImprovement(state.session.retryAttempt, action.answer)
          : state.session.retryAttempt
      return {
        ...state,
        session: {
          ...state.session,
          firstAttempt,
          retryAttempt,
        },
        history: state.history.map((record) =>
          record.id === state.session?.id
            ? {
                ...record,
                firstAttempt:
                  action.attempt === 1
                    ? (withHigherImprovement(record.firstAttempt, action.answer) ??
                      record.firstAttempt)
                    : record.firstAttempt,
                retryAttempt:
                  action.attempt === 2
                    ? withHigherImprovement(record.retryAttempt, action.answer)
                    : record.retryAttempt,
              }
            : record,
        ),
      }
    }
    case 'OPEN_RECORD':
      return {
        ...state,
        view: 'feedback',
        session: {
          id: action.record.id,
          question: action.record.question,
          profileSnapshot: action.record.profileSnapshot,
          attempt: action.record.retryAttempt ? 2 : 1,
          transcript:
            action.record.retryAttempt?.transcript ?? action.record.firstAttempt.transcript,
          firstAttempt: action.record.firstAttempt,
          retryAttempt: action.record.retryAttempt,
          comparison: action.record.comparison,
        },
      }
    case 'DELETE_RECORD':
      return {
        ...state,
        history: state.history.filter((record) => record.id !== action.id),
        session: state.session?.id === action.id ? null : state.session,
        view: state.session?.id === action.id ? 'history' : state.view,
      }
    case 'CLEAR_HISTORY':
      return {
        ...state,
        history: [],
        session: state.view === 'history' ? null : state.session,
      }
    default:
      return state
  }
}
