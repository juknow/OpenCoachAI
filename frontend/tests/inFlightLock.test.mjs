import assert from 'node:assert/strict'
import test from 'node:test'
import { runWithInFlightLock } from '../src/services/inFlightLock.ts'

test('rapid duplicate actions execute the request only once', async () => {
  const lock = { current: false }
  let calls = 0
  let release
  const pending = new Promise((resolve) => {
    release = resolve
  })
  const operation = async () => {
    calls += 1
    await pending
    return 'done'
  }

  const first = runWithInFlightLock(lock, operation)
  const duplicate = runWithInFlightLock(lock, operation)
  assert.equal(calls, 1)
  assert.equal(await duplicate, undefined)
  release()
  assert.equal(await first, 'done')
  assert.equal(lock.current, false)
})

test('the lock is released after a failed request', async () => {
  const lock = { current: false }
  await assert.rejects(
    runWithInFlightLock(lock, async () => {
      throw new Error('expected')
    }),
  )
  assert.equal(lock.current, false)
})
