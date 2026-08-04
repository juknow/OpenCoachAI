# Shared idempotency deployment gate

The current `ResultCache` protocol is implemented by the bounded in-process
`EvaluationCache`. It provides TTL result reuse and single-flight coalescing inside
one FastAPI process. It cannot prevent duplicate local evaluation work across workers or
hosts.

Use a Redis-compatible shared adapter before deploying multiple backend instances.
The adapter must preserve this contract:

1. Hash keys are created from request type, model, prompt/schema versions, prompt
   hash, and canonical request JSON. Never include an API key in key material.
2. Store only the validated response needed for replay, with the configured TTL.
   Never store audio, raw prompt text, or an unhashed transcript in cache keys or
   logs.
3. Acquire a short distributed lease for a cache miss, renew it while the provider
   call is in flight, and let duplicate callers wait for the validated result.
4. Use an owner token for lease release so one worker cannot release another
   worker's lease. If the owner fails, the lease must expire safely.
5. Do not cache failures, incomplete Structured Outputs, or validation errors.
6. Replace `requestId` on every HTTP response, including a cache hit.
7. Namespace evaluation-v2 and higher-answer entries separately and include model,
   prompt, and schema versions so a rollout cannot replay an incompatible result.

Required rollout tests are the existing hit/coalescing/failure tests plus a
two-client integration test against the shared store, lease-expiry recovery, cache
version invalidation, and verification that logs and keys contain no transcript or
secret. Keep the memory adapter as the local-development fallback. A Redis package
is intentionally not installed until horizontal deployment is actually required.
