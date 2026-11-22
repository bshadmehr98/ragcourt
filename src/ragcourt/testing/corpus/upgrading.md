Larkspur Docs · version 3.2

# Upgrading

Upgrades between minor versions need no downtime. Upgrade the package, run the migrations, then restart
the workers one at a time. Version 3.2 was released on 4 March 2026 and is supported until 3.4 comes out.

## From 3.1 to 3.2

Version 3.2 adds the heartbeat column and the `dead` state. Before 3.2, a job that used up its attempts
stayed `failed`; the migration turns those rows into `dead` jobs.

The `migrate` command creates three tables in a schema named `larkspur` and never touches any other
schema. Running it twice is safe: it only applies the migrations that are not there yet.

## After the upgrade

Enqueue a test job from a Python shell and watch the worker log. A healthy worker prints one line when
it takes the job and one line when it finishes, with the job's id and how long it ran in milliseconds.
If nothing appears after a few seconds, check that the worker and the application use the same
database URL and the same queue name, because a worker only takes jobs from the queues it was assigned.

## From 2.x

Version 2 stored jobs in Redis. There is no automatic path from 2.x: drain the old queues, then start
version 3 on an empty database. Version 2 reached its end of life on 31 December 2025 and receives no
security fixes.

Edit this page on the Larkspur wiki · Larkspur contributors
