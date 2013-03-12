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
        if not utask.should_sync():
            continue

        known_tasks = [t for t in dtasks if t.is_associated_with(utask)]
        if len(known_tasks) == 0:
            log.debug("Upstream {0} isn't known downstream.", utask)
            downstream_q.append((utask, None))
        else:
            for dtask in known_tasks:
                dtasks.discard(dtask)
                if dtask == utask:
                    log.debug("Tasks {0} and {1} are up-to-date.", utask, dtask)
                elif dtask.stale(utask):
                    log.info("Sync required {0}->{1}.", utask, dtask)
                    downstream_q.append((utask, dtask))
                else:
                    # Downstream wins (no other way to solve this).
                    log.info("Sync required {0}->{1}.", dtask, utask)
                    upstream_q.append((dtask, utask))

    # The remaining tasks in the downstream task list are not known upstream.
    # It's possible that a task is being excluded from syncronization. Check it.
    for dtask in dtasks:
        if not dtask.should_sync():
            continue

        elif dtask.association is None:
            # An unknown task.
            upstream_q.append((dtask, None))
        else:
            downstream_q.append((None, dtask))

    __sync_tasks(execution['upstream'], execution['downstream'], downstream_q)
    __sync_tasks(execution['downstream'], execution['upstream'], upstream_q)


def __delete_orphan(dest, dest_batch, dest_task):
    if not dest['delete_orphans']:
        log.info("Skipping orphan, {0}.", dest_task)
        return False
    log.info("Deleting orphan for {0}.", dest_task)
    dest['repository'].delete(dest_task, dest_batch, None, None)
    return True

def __sync_task(source, source_batch, source_task, dest, dest_batch, dest_task):
    dest_task.copy_from(source_task)

    task_cb = dest['cb']
    if not task_cb is None:
        task_cb(source_task, dest_task)

    def task_created(dest_task, source_task):
        if not isinstance(source_task, tasksync.DownstreamTask):
            # A sync is only required when the source is a downstream task.
            return
        log.info("Successfully synced {0}->{1}.", source_task, dest_task)
        if source_task.association is None:
            source_task.copy_from(dest_task)
            source['repository'].save(source_task, source_batch, None, None)

    dest['repository'].save(dest_task, dest_batch, task_created, source_task)

def __sync_tasks(source, dest, queue):
    if(len(queue) < 1):
        return

    source_batch = source['repository'].batch_open()

    dest_batch = dest['repository'].batch_open()
    for (source_task, dest_task) in queue:
        if source_task is None or source_task.is_deleted:
            log.info("Identified orphan for {0}.", dest_task)
            __delete_orphan(dest, dest_batch, dest_task)
            continue
        elif dest_task is None:
            # The destination task isn't known. It's either orphaned or new.
            dest_task = dest['factory'].create_from(other=source_task)
            log.debug("Created {0} from {1}.", dest_task, source_task)

        if not dest_task.should_sync_with(source_task):
            log.debug("Skipping sync for rule {0}->{1}", source_task, dest_task)
            continue

        task_filter = dest['filter']
        if not task_filter is None and not task_filter(source_task, dest_task):
            log.debug("Skipping sync for {0}->{1}", source_task, dest_task)
            continue
        else:
            log.info("Syncing {0}->{1}", source_task, dest_task)
            __sync_task(source, source_batch, source_task,
                    dest, dest_batch, dest_task)

    dest['repository'].batch_close(dest_batch)
    source['repository'].batch_close(source_batch)

def main():
    """ Main method. """
    twiggy.quickSetup(min_level=twiggy.levels.INFO, file=sys.stdout)

    for execution in tasksync.config.executions:
        log.info("Running {0}.", execution)
        sync_all(tasksync.config.executions[execution])

if __name__ == "__main__":
    main()
