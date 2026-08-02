import type { CoachService } from './coachService.ts'

export const createOpenAIService = (): CoachService => {
  throw new Error(
    'The OpenAI provider is intentionally disabled in this migration stage.',
  )
}
