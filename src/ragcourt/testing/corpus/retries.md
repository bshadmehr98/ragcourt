Larkspur Docs · version 3.2

# Retries

When a job raises an exception, Larkspur records the error and tries the job again later. A job is
attempted at most five times by default; after the last failed attempt it is marked dead and is never
retried automatically.

## The retry delay

The delay before the next attempt grows with each failure. The first retry waits 10 seconds, and each
later retry waits three times as long as the one before, so the attempts of a job that keeps failing are
spread over about twenty minutes. A random jitter of up to 20 percent is added to each delay, so that
many jobs failing at the same moment do not all retry at the same moment.

## Errors that are not retried

Some failures will not go away by waiting. A job whose function raises `larkspur.Abort` is marked dead at
once, without using its remaining attempts. A job whose arguments cannot be decoded is also not retried,
since every attempt would fail in the same way. Exceptions raised by the database while the worker is
saving the job's result are the exception to this rule: they are always retried, because the job itself
may have succeeded.

## Retries and timeouts are different

A retry happens after a job failed. A timeout stops a job that is still running. A job stopped by its
timeout counts as a failed attempt and is then retried like any other failure, unless it has no attempts
left.

Edit this page on the Larkspur wiki · Larkspur contributors
