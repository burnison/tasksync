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

""" Realization of TaskWarrior tasks. """
import taskw
import tasksync

from datetime import datetime
from twiggy import log

class TaskWarriorTask(tasksync.Task, tasksync.DownstreamTask):
    """ Represents a TaskWarrior task. """
    __UDA_NAMESPACE = "tasksync"
    __UDA_ASSOCIATION = "%s_assoc" % __UDA_NAMESPACE
    __UDA_ETAG = "%s_etag" % __UDA_NAMESPACE

    def __init__(self, source):
        super(TaskWarriorTask, self).__init__()
        self._source = source

    def __str__(self):
        return "%s[id=%s,p=%s,s=%s]" % (
                'TaskWarriorTask', self.uid, self.project, self.subject)

    def stale(self, other):
        """ Identifies if this task is stale from upstream. """
        if not TaskWarriorTask.__UDA_ETAG in self._source:
            # Is local only. Couldn't possibly be upstream.
            return False
        return self._source[TaskWarriorTask.__UDA_ETAG] != other.etag

    def copy_from(self, other):
        if other is None:
            raise ValueError("Cannot sync with nothing.")

        self.__set_or_delete('project', getattr(other, 'project', None))
        self.__set_or_delete('description', other.subject)

        dfmt = self.__format_date # Format callback.
        self.__set_or_delete('due', other.due, fmt=dfmt)
        self.__set_or_delete('end', other.completed, fmt=dfmt)

        self.associate_with(other)

    def should_sync(self):
        if self.is_deleted:
            # A deleted task doesn't really exist.
            return False
        elif self.is_recurring:
            # Don't send these upstream. They're effectively factories.
            return False
        elif self.is_completed and self.association is None:
            # The task was completed locally before it was ever created
            # upstream. Probably not much value sending this up.
            return False
        else:
            return True

    def should_sync_with(self, other):
        if self.is_completed and other.is_pending:
            # The task was marked done then reopened upstream. Effectively,
            # the task was reopened. This isn't supported (for now).
            log.warning("Reopening of {0} is not supported.", self)
            return False
        else:
            return True

    @property
    def is_recurring(self):
        """ Identifies if this is a recurring task. """
        return self.status == 'recurring'

    @property
    def uid(self):
        return self._source.get('uuid', None)

    @property
    def etag(self):
        return self._source.get(TaskWarriorTask.__UDA_ETAG)

    @property
    def status(self):
        return self._source['status']

    @property
    def project(self):
        return self._source.get('project', None)

    @property
    def subject(self):
        return self._source['description']

    @property
    def due(self):
        return self.__parse_date(self._source.get('due', None))

    @property
    def completed(self):
        return self.__parse_date(self._source.get('end', None))

    @property
    def annotations(self):
        """ Gets a dict of annotations. """
        annotations = {}
        for key in self._source.keys():
            if key.startswith('annotation_'):
                annotations[key] = self._source[key]
        return annotations

    @property
    def association(self):
        """ Gets the upstream identifier for this task. """
        for key in self._source.keys():
            if key.startswith(TaskWarriorTask.__UDA_ASSOCIATION):
                return self._source[key]
        return None

    def is_associated_with(self, other):
        """ Identifies if this task is associated with the specified task. """
        association_key = self._association_key_for(other)
        if association_key in self._source:
            return self._source[association_key] == other.uid
        return False

    def associate_with(self, other):
        """ Associate the specified associable with this instance.  """
        association_key = self._association_key_for(other)
        self._source[association_key] = other.uid
        self._source[TaskWarriorTask.__UDA_ETAG] = other.etag

    def _association_key_for(self, upstream):
        """ Generate the association key for the upstream. """
        return "%s_%s" % (TaskWarriorTask.__UDA_ASSOCIATION, upstream.provider)

    def __parse_date(self, as_string):
        if as_string is None:
            return None
        return datetime.fromtimestamp(int(as_string))

    def __format_date(self, as_timestamp):
        return datetime.strftime(as_timestamp, '%s')

    def __set_or_delete(self, key, value, fmt=None):
        if value is None:
            if key in self._source:
                del self._source[key]
        else:
            if not fmt is None:
                value = fmt(value)
            self._source[key] = value

class TaskWarriorTaskFactory(tasksync.TaskFactory):
    def create_from(self, **kwargs):
        """ Create a new task from another task, 'other', or a map, 'map'. """
        if 'map' in kwargs:
            return TaskWarriorTask(kwargs['map'].copy())

        elif 'other' in kwargs:
            task = TaskWarriorTask({'status':'pending'})
            task.copy_from(kwargs['other'])
            return task

        raise KeyError('Either a map or task argument must be provided.')

class TaskWarriorTaskRepository(tasksync.TaskRepository):
    def __init__(self, factory, db=None, **kwargs):
        self._db = db or taskw.TaskWarrior(config_filename=kwargs['config'])
        self._factory = factory

    def all(self):
        wtasks = self._db.load_tasks()
        wtasks = sum(wtasks.values(), [])
        return [self._factory.create_from(map=t) for t in wtasks]

    def batch_open(self):
        return {'count':0, 'create':[], 'update':[], 'delete':[]}

    def batch_close(self, batch):
        for (m, c, u) in batch['create']:
            self._close(self._db.task_add(**m), c, u)

        for (m, c, u) in batch['update']:
            self._db.task_update(m)
            self._close(m, c, u)

        for (m, c, u) in batch['delete']:
            self._db.task_delete(uuid=m['uuid'])
            if not c is None:
                c(None, u)

    def _close(self, source, cb, userdata):
        task = self._factory.create_from(map=source)

        # Task completion is a special case.
        if task.is_pending and not task.completed is None:
            log.info("Marking {0} as complete.", task)
            keys = {k:task._source[k]
                    for k in task._source.keys()
                    if k == 'uuid' or k == 'end'}
            task._source = self._db.task_done(**keys)

        if not cb is None:
            cb(task, userdata)

    def delete(self, task, batch, cb, userdata):
        batch['delete'].append((task._source, cb, userdata))

    def save(self, task, batch, cb, userdata):
        if task.uid is None:
            batch['create'].append((task._source, cb, userdata))
        else:
            batch['update'].append((task._source, cb, userdata))
