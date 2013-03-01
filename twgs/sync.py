#pylint: disable=C0111
import os
import sys
import twiggy
import twgs

from twiggy import log

def sync_all(wtr, wtf, gtr, gtf):
    """ Pulls down the task list. """
    wtasks = set(wtr.all())
    gtasks = set(gtr.all())

    upstream_q = []
    downstream_q = []
    downstream_orphans = wtasks
    for gtask in gtasks:
        known_tasks = [t for t in wtasks if t.is_associated_with(gtask)]
        # The current task doesn't have a local counterpart.
        if len(known_tasks) == 0:
            downstream_q.append((gtask, None))
            log.debug("Upstream {0} isn't known locally.", gtask)
        # One or more local tasks is mapped to this source.
        else:
            for wtask in known_tasks:
                downstream_orphans.discard(wtask)
                if wtask == gtask:
                    log.debug("Task {0}->{1} is up-to-date.", wtask, gtask)
                    continue
                # Because local doesn't specify an etag, this means upstream
                # has changed. There's a chance we have a 2-way diff, but
                # that's not of concern---yet.
                elif wtask.stale(gtask):
                    log.debug("Sync required {0}->{1}.", wtask, gtask)
                    downstream_q.append((gtask, wtask))
                else:
                    log.debug("Sync required {0}->{1}.", gtask, wtask)
                    upstream_q.append((wtask, gtask))

    # All locally-managed tasks that are not known upstream.  This may also
    # include orphaned tasks that were previously managed upstream.
    for wtask in downstream_orphans:
        if wtask.should_sync:
            if wtask.association is None:
                upstream_q.append((wtask, None))
            else:
                log.info("Deleting orphaned local task, {0}.", wtask)
                wtr.delete(wtask)

    __sync_downstream(wtr, wtf, downstream_q)
    __sync_upstream(wtr, gtr, gtf, upstream_q)

def __sync_downstream(wtr, wtf, queue):
    """ Updates the local task to match the upstream source. """
    for (gtask, wtask) in queue:
        # The task isn't managed locally. Create it.
        if wtask is None:
            wtask = wtf.create_from(other=gtask)
            wtask.associate_with(gtask)
            log.info("Created {0} from {1}.", wtask, gtask)
        else:
            # Taskwarrior's structure doesn't really support this action.
            # In the future, perhaps a unassociate+new will make sense, but
            # a log should be fine for now.
            if wtask.is_completed and gtask.is_pending:
                log.warning("Reopening of {0} is not supported.", wtask)
                continue

            log.info("Downstream update required for {0}->{1}", gtask, wtask)
            wtask.copy_from(gtask)
            wtask.associate_with(gtask)
        wtr.save(wtask)

def __sync_upstream(wtr, gtr, gtf, queue):
    """ Updates the upstream task to match the local source. """
    if(len(queue) < 1):
        return

    # Keep things simple: use a registry.
    batch_size = 0
    batch = gtr.batch_create()

    def task_created(gtask, wtask):
        log.info("Syncing local {0}->{1}.", wtask, gtask)
        wtask.copy_from(gtask)
        wtask.associate_with(gtask)
        wtr.save(wtask)

    for (wtask, gtask) in queue:
        # This is an unknown task.
        if gtask is None:
            gtask = gtf.create_from(other=wtask)
            gtr.save(gtask, batch=batch, userdata=wtask, cb=task_created)
            log.info("Created {0} from {1}.", gtask, wtask)
        else:
            if wtask.is_deleted:
                log.info("Upstream delete required for {0}->{1}", wtask, gtask)
                gtr.delete(gtask, batch=batch)
            else:
                log.info("Upstream update required for {0}->{1}", wtask, gtask)
                gtask.copy_from(wtask)
                gtr.save(gtask, batch=batch, userdata=wtask, cb=task_created)

        batch_size += 1

    if(batch_size > 0):
        gtr.batch_close(batch)

def main():
    """ Main method. """
    twiggy.quickSetup(min_level=twiggy.levels.INFO, file=sys.stdout)

    import config
    if not os.path.exists(config.home):
        log.info('Making home directory, {0}', config.home)
        os.makedirs(config.home)

    wtf = twgs.TaskWarriorTaskFactory()
    wtr = twgs.TaskWarriorTaskRepository(wtf, **config.providers.taskwarrior)

    gtf = twgs.GoogleTaskFactory()
    gtr = twgs.GoogleTaskRepository(gtf, **config.providers.google)

    sync_all(wtr, wtf, gtr, gtf)

if __name__ == "__main__":
    main()
