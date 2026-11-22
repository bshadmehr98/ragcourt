Larkspur Docs · version 3.2

# Installing Larkspur

Larkspur needs Python 3.10 or newer and PostgreSQL 13 or newer. It runs on Linux and macOS. Windows is
not supported: the worker relies on POSIX signals to shut down cleanly, and there is no equivalent that
behaves the same way.

## Install the package

Install Larkspur from the package index into the same environment as your application:

```bash
pip install larkspur==3.2.1
larkspur migrate --database-url postgresql://localhost/app
larkspur worker --queues default,email
```

The `migrate` command creates three tables in a schema named `larkspur` and never touches any other
schema. Running it twice is safe: it only applies the migrations that are missing.

## Check that it works

Enqueue a test job from a Python shell and watch the worker log. A healthy worker prints one line when
it takes the job and one line when it finishes, with the job's id and how long it ran in milliseconds.
If nothing appears after a few seconds, check that the worker and the application use the same
database URL and the same queue name, because a worker only takes jobs from the queues it was given.

## Before going to production

Run at least two workers so that a deploy or a crash never leaves a queue without anyone to serve it.
Give each worker a memory limit, keep the database connection pool larger than the number of worker
threads, and schedule the sweeper described in the scheduling guide so that finished jobs do not pile up
in the jobs table for ever.

Edit this page on the Larkspur wiki · Larkspur contributors
