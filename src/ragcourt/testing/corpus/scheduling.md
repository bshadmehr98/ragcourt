Larkspur Docs · version 3.2

# Scheduling

Jobs can run later or on a schedule. A job enqueued with `run_at` waits until that time; a periodic job
is enqueued by the scheduler at the times its schedule gives.

## Periodic jobs

A periodic job is declared with a cron expression, e.g. a report every weekday at seven in the morning:

    @larkspur.periodic("0 7 * * 1-5", queue="reports")
    def weekday_report():
        build_report(day=date.today())

The scheduler runs inside every worker, and the workers agree through the database which of them
enqueues each run, so a periodic job runs once per scheduled time however many workers there are.
Missed runs are not made up: if every worker is down at seven, that morning's report is skipped.

## The sweeper

The sweeper is a periodic job that ships with Larkspur, named `lark-sweeper`. It runs approx. every ten
minutes and does two things. It returns jobs whose heartbeat stopped to their queue, and it deletes
finished jobs older than the retention period. Dead jobs are never deleted by the sweeper.

Edit this page on the Larkspur wiki · Larkspur contributors
