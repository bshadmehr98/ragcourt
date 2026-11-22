Larkspur Docs · version 3.2

# Configuration

Every setting can be given as an environment variable or in `larkspur.toml`. An environment variable
wins over the file. Durations are in seconds unless the name says otherwise.

| Setting | Environment variable | Default | What it does |
|---|---|---|---|
| database_url | LARKSPUR_DATABASE_URL | none | where the jobs table lives |
| queues | LARKSPUR_QUEUES | default | the queues a worker takes jobs from |
| concurrency | LARKSPUR_CONCURRENCY | 4 | jobs one worker runs at the same time |
| max_inflight | LARKSPUR_MAX_INFLIGHT | 200 | jobs taken but not finished, across all workers |
| poll_interval | LARKSPUR_POLL_INTERVAL | 2 | seconds between polls when no notification arrives |
| job_timeout | LARKSPUR_JOB_TIMEOUT | 300 | seconds before a running job is stopped |
| max_attempts | LARKSPUR_MAX_ATTEMPTS | 5 | attempts before a job is marked dead |
| retention_days | LARKSPUR_RETENTION_DAYS | 14 | days finished jobs are kept before the sweeper removes them |

## Choosing the concurrency

Concurrency is per worker. A worker with a concurrency of 4 runs up to four jobs at once, each in its own
thread. Jobs that mostly wait on the network can use a higher value; jobs that keep a processor busy
should use a value close to the number of cores.

## The in-flight limit

The in-flight limit protects the database. When it is reached, workers stop taking new jobs until some
finish, even if they have free threads. Raise it only after checking that the database can hold that
many open transactions.

Edit this page on the Larkspur wiki · Larkspur contributors
