Larkspur Docs · version 3.2

# Timeouts

Every running job has a timeout. When a job runs longer than its timeout, Larkspur stops it and records
the attempt as failed. The default timeout is 300 seconds, and a job can set its own when it is enqueued.

## How a job is stopped

The worker runs each job in a thread and checks the clock every second. When the timeout passes, the
worker raises an exception inside the job's thread at its next Python instruction. Code that is blocked
inside a C extension, for example waiting on a socket without its own timeout, cannot be interrupted this
way; the worker then marks the attempt as failed, abandons the thread, and restarts itself after the
current jobs finish.

## The drain timeout

When a worker is asked to stop, it stops taking new jobs and waits for the running ones to finish. The
`--drain-timeout` option, 30 seconds by default, sets how long it waits. Jobs still running after the
drain timeout are returned to their queue and attempted again by another worker, and the attempt is not
counted against them.

## Timeouts and retries are different

A timeout stops a job that is still running. A retry happens after a job failed. A job stopped by its
timeout is retried like any other failure, so a job that always runs too long will use all its attempts
and end up dead.

Edit this page on the Larkspur wiki · Larkspur contributors
