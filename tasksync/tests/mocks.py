# Copyright (C) 2012-2018 Richard Burnison
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

#pylint: disable=C0103,C0111,I0011,I0012,W0704,W0142,W0212,W0232,W0613,W0702
#pylint: disable=R0201,W0614,R0914,R0912,R0915,R0913,R0904,R0801,W0201,R0902
from tasksync.task import Task, DownstreamTask, UpstreamTask

import copy

class MockTask(Task):
    def __init__(self, **kwargs):
        self._uid = kwargs.get('uid', None)
        self._status = kwargs.get('status', None)
        self._subject = kwargs.get('subject', None)
        self._completed = kwargs.get('completed', None)
        self._due = kwargs.get('due', None)
        self._provider = kwargs.get('provider', None)
        self._etag = kwargs.get('etag', None)

    def as_dict(self):
        d = {
            'uid': self._uid,
            'status': self._status,
            'subject': self._subject,
            'completed': self._completed,
            'due': self._due,
            'provider': self._provider,
            'etag': self._etag,
        }
        return { k:v for k,v in d.items() if v is not None }


    def should_sync(self):
        return True

    def should_sync_with(self, other):
        return True

    @property
    def uid(self):
        return self._uid

    @property
    def etag(self):
        return self._etag

    @property
    def status(self):
        return self._status

    @property
    def subject(self):
        return self._subject

    @property
    def completed(self):
        return self._completed

    @property
    def due(self):
        return self._due

    def copy_from(self, other):
        return copy.copy(self)

class MockDownstreamTask(MockTask, DownstreamTask):
    def __init__(self, **kwargs):
        super(MockDownstreamTask, self).__init__()
        self.upstream = kwargs.get('upstream', None)

    def mark_dirty(self):
        self._etag = 'dirty'

    def is_associated_with(self, upstream):
        return self.upstream == upstream

    def associate_with(self, upstream):
        self.upstream = upstream

    @property
    def association(self):
        if self.upstream is None:
            return None
        return self.upstream.uid

    def stale(self, other):
        return self._etag != other._etag

class MockUpstreamTask(MockTask, UpstreamTask):
    def __init__(self, **kwargs):
        super(MockUpstreamTask, self).__init__(**kwargs)
        self._provider = kwargs.get('provider', None)
        self._etag = kwargs.get('etag', None)

    @property
    def provider(self):
        return self._provider
