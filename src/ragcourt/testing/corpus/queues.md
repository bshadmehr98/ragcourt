Larkspur Docs · version 3.2

# Queues

A queue is a name. Jobs are enqueued under a name, and a worker is told which names to serve. Nothing
needs to be created in advance: the first job enqueued under a new name creates the queue.

## How a job moves through a queue

When the application enqueues a job, Larkspur inserts one row into the jobs table with the state
`waiting`, the queue's name, the job's arguments as JSON and the time it may run, which is now unless the
job was scheduled for later. In the same transaction it sends a notification on a channel named after the
queue. Because the row and the notification are committed together, a worker never hears about a job
that does not exist yet, and a job enqueued inside a transaction that is rolled back simply never
happens. This is the main reason Larkspur keeps its jobs in the same database as the application: the job
and the data it works on change together or not at all.

A worker listens on the channels of its queues. When a notification arrives, or when the poll interval
passes without one, the worker asks the database for the oldest waiting job on its queues whose run time
has come. It asks with a locking read that skips rows other workers have already locked, so two workers
never take the same job and neither waits for the other. The worker marks the row as `running`, records
its own name and the time it started, commits, and then calls the job's function with the stored
arguments. Holding no transaction open while the job runs keeps the database free of long transactions,
which would otherwise block the vacuum and slowly bloat every table.

While the job runs, the worker writes a heartbeat to the row every few seconds. The heartbeat is how the
rest of the system knows the job is still alive. If a worker is killed, its heartbeats stop, and after
the job timeout the sweeper sees a running job with an old heartbeat and returns it to the queue as a
failed attempt. The job is then retried like any other failure, so a crash costs one attempt and some
time, but the job is not lost.

When the function returns, the worker marks the row `finished` with the time it ended. When the function
raises an exception, the worker records the error's type and message, counts the attempt, and either
schedules the next attempt according to the retry policy or, when the attempts are used up, marks the job
`dead`. A dead job stays in the table with its last error until someone looks at it. Larkspur does not
delete dead jobs on its own, because a dead job is usually a bug that someone needs to read about.

Order within a queue is by run time and then by the time the job was enqueued. Larkspur does not promise
strict order across workers: two jobs enqueued a millisecond apart may run at the same moment on two
workers, and the second may finish first. Jobs that must run one after another should be enqueued one
after another, each by the job before it, or sent to a queue served by a single worker with a concurrency
of one.

Priorities are not a separate mechanism. A team that needs urgent jobs to go first puts them on their own
queue and gives that queue its own workers, so a burst of ordinary work can never delay them. This is
simpler to reason about than numeric priorities, and it makes the capacity reserved for urgent work
visible in the deployment instead of hidden in the data.

## Pausing a queue

A queue can be paused with `larkspur pause NAME`. Workers stop taking new jobs from it, and the jobs
already running finish normally. Jobs can still be enqueued while the queue is paused; they wait until it
is resumed with `larkspur resume NAME`.

Edit this page on the Larkspur wiki · Larkspur contributors
