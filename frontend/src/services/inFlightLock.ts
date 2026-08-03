export interface InFlightLock {
  current: boolean
}

export const runWithInFlightLock = async <Result>(
  lock: InFlightLock,
  operation: () => Promise<Result>,
): Promise<Result | undefined> => {
  if (lock.current) return undefined
  lock.current = true
  try {
    return await operation()
  } finally {
    lock.current = false
  }
}
