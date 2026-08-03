import type { CoachService } from './coachService.ts'
import type { CoachProvider } from '../types/coach.ts'
import { httpCoachService } from './httpCoachService.ts'
import { mockCoachService } from './mockCoachService.ts'

export const getCoachService = (provider: CoachProvider): CoachService =>
  provider === 'openai' ? httpCoachService : mockCoachService
