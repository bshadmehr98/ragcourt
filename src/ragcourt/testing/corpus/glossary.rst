Glossary
========

Larkspur uses a few words in a precise sense. This page defines them.

Attempt
-------

One run of a job's function. A job that fails is attempted again until it succeeds or reaches the
maximum number of attempts.

Dead job
--------

A job that failed on its last attempt, or raised ``larkspur.Abort``. Dead jobs stay in the table until
someone deletes them by hand or retries them from the dashboard.

Heartbeat
---------

The time a running job last reported that it was alive. The sweeper uses it to find jobs whose worker
has died.

In-flight job
-------------

A job a worker has taken and not yet finished. The number of in-flight jobs across all workers is
limited by ``max_inflight``.
