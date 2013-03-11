# Copyright (C) 2012 Richard Burnison
#
# This file is part of tasksync.
#
# tasksync is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# tasksync is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with tasksync.  If not, see <http://www.gnu.org/licenses/>.

#pylint: disable=C0111
import sys
import twiggy
import tasksync

from twiggy import log

def sync_all(execution):
    """ Pulls down the task list. """
    dtasks = set(execution['downstream']['repository'].all())
    utasks = set(execution['upstream']['repository'].all())

    upstream_q = []
    downstream_q = []

    for utask in utasks:
        # Skip anything that shouldn't be synced.
        if not utask.should_sync:
            continue

        known_tasks = [t for t in dtasks if t.is_associated_with(utask)]
        # The current task doesn't have a local counterpart.
        if len(known_tasks) == 0:
            downstream_q.append((utask, None))
            log.debug("Upstream {0} isn't known locally.", utask)
        else:
            for dtask in known_tasks:
                dtasks.discard(dtask)
                if dtask == utask:
                    log.debug("Task {0}->{1} is up-to-date.", dtask, utask)
                    continue
                elif dtask.stale(utask):
                    log.debug("Sync required {0}->{1}.", dtask, utask)
                    downstream_q.append((utask, dtask))
                else:
                    log.debug("Sync required {0}->{1}.", utask, dtask)
                    upstream_q.append((dtask, utask))

    # The remaining tasks in the downstream task list are not known upstream.
    # It's possible that a task is being excluded from syncronization. Check it.
    for dtask in dtasks:
        if dtask.should_sync:
            if dtask.association is None:
                upstream_q.append((dtask, None))
            else:
                downstream_q.append((None, dtask))

    __sync_downstream(execution, downstream_q)
    __sync_upstream(execution, upstream_q)

def __sync_downstream(execution, queue):
    """
    Updates the local task to match the upstream source.
    """
    # FIXME: Cyclomatic complexity a bit too high.
    for (utask, dtask) in queue:
        if dtask is None:
            # The task isn't managed locally. Create it.
            dtask = execution['downstream']['factory'].create_from(other=utask)
            dtask.associate_with(utask)
            log.info("Created {0} from {1}.", dtask, utask)

        task_filter = execution['downstream']['filter']
        if not task_filter is None and not task_filter(utask, dtask):
            log.info("Skipping sync for {0}->{1}", utask, dtask)
            continue

        elif utask is None:
            if not dtask.association is None:
                # Associated task was deleted upstream.
                if execution['downstream']['delete_orphans']:
                    log.info("Deleting orphaned local task, {0}.", dtask)
                    execution['downstream']['repository'].delete(dtask)
                    continue
                else:
                    log.info("Skipping orphan, {0}.", dtask)
            else:
                # This'd mean there's a bug in the enqueuing algorithm.
                log.error("Received unmanaged downstream task, {0}.", dtask)
        else:
            log.info("Downstream sync required for {0}->{1}", utask, dtask)
            if dtask.is_completed and utask.is_pending:
                # TODO: Add reopening support.
                log.warning("Reopening of {0} is not supported.", dtask)
                continue
            else:
                dtask.copy_from(utask)
                dtask.associate_with(utask)

        task_cb = execution['downstream']['cb']
        if not task_cb is None:
            task_cb(utask, dtask)

        execution['downstream']['repository'].save(dtask)

# TODO: Merge this function with the downstream sync. Too much redundancy.
# FIXME: This is tightly coupled with Google Tasks. Can't really be reused much.
def __sync_upstream(execution, queue):
    """
    Updates the upstream task to match the local source.
    """
    if(len(queue) < 1):
        return

    # Keep things simple: use a registry.
    batch = execution['upstream']['repository'].batch_create()
    def task_created(utask, dtask):
        log.info("Syncing local {0}->{1}.", dtask, utask)
        dtask.copy_from(utask)
        dtask.associate_with(utask)
        execution['downstream']['repository'].save(dtask)

    # FIXME: Cyclomatic complexity a bit too high.
    for (dtask, utask) in queue:
        if utask is None:
            # The task isn't known upstream.
            utask = execution['upstream']['factory'].create_from(other=dtask)
            log.info("Created {0} from {1}.", utask, dtask)

        task_filter = execution['upstream']['filter']
        if not task_filter is None and not task_filter(dtask, utask):
            log.info("Skipping sync for {0}->{1}", dtask, utask)
            continue

        elif dtask.is_deleted:
            if execution['upstream']['delete_orphans']:
                log.info("Upstream delete required for {0}->{1}", dtask, utask)
                execution['upstream']['repository'].delete(utask, batch=batch)
            else:
                log.info("Skipping orphan, {0}.", utask)
        else:
            log.info("Upstream sync required for {0}->{1}", dtask, utask)
            utask.copy_from(dtask)

            task_cb = execution['upstream']['cb']
            if not task_cb is None:
                task_cb(dtask, utask)

            execution['upstream']['repository'].save(utask, batch=batch, userdata=dtask, cb=task_created)

    execution['upstream']['repository'].batch_close(batch)

def main():
    """ Main method. """
    twiggy.quickSetup(min_level=twiggy.levels.INFO, file=sys.stdout)

    for execution in tasksync.config.executions:
        log.info("Running {0}.", execution)
        sync_all(tasksync.config.executions[execution])

if __name__ == "__main__":
    main()
