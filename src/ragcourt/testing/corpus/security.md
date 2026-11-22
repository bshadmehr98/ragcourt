# Security

Larkspur stores a job's arguments in the database as JSON, in plain text. Do not put secrets such as
passwords or tokens in job arguments; store a reference to the secret and look it up inside the job.

## What is logged

Worker logs contain the job's id, its queue, its function name, its state and how long it ran. Job
arguments are never logged, and neither are the error messages of failed jobs, because both may hold
personal data. The error messages are kept in the jobs table, where the database's access rules apply.

## Signed jobs

When `signing_key` is set, every job is signed with HMAC-SHA256 when it is enqueued, and a worker refuses
to run a job whose signature does not match. Signing protects against someone who can write to the jobs
table but cannot read the key. It does not encrypt the arguments: anyone who can read the table can still
read them.

## The dashboard

The dashboard has no login of its own. It must not be exposed to the internet; put it behind the same
authentication as your other internal tools. It shows arguments only to users with the `larkspur_admin`
database role, except in development mode, where everything is shown.
