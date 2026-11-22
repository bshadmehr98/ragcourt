Larkspur Docs · version 3.2

# Larkspur

Larkspur is a small job queue for teams that run their own servers. A web application hands Larkspur a
job, such as sending an email or resizing an image, and a worker process picks it up a moment later. The
application does not wait for the work to finish, so pages stay fast even when the work is slow.

Larkspur keeps its jobs in PostgreSQL. There is no separate broker to install, back up or monitor: if
you already run PostgreSQL, you already run everything Larkspur needs. A job is a row; a queue is a
name on that row; a worker is a process that asks the database for the next row it may take.

## Who it is for

Larkspur suits teams with up to a few thousand jobs per minute who would rather not operate a message
broker. Teams that need hundreds of thousands of jobs per second, or delivery across data centres,
should look at a dedicated broker instead. Larkspur says so plainly because a queue that is too small
for its load fails in ways that are hard to see until the backlog is hours long.

## Where to go next

Start with the installation guide, then read how queues work and how retries and timeouts differ. The
configuration reference lists every setting with its default. The security page explains what Larkspur
stores and what it never writes to its logs.

Edit this page on the Larkspur wiki · Larkspur contributors
