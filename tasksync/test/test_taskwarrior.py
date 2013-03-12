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

#pylint: disable=C0103,C0111,I0011,I0012,W0704,W0142,W0212,W0232,W0613,W0702
#pylint: disable=R0201,W0614,R0914,R0912,R0915,R0913,R0904,R0801,W0201,R0902
import datetime
import tasksync

from mocks import MockUpstreamTask
from mockito import mock, when, verify, any
from nose.tools import raises, eq_, ok_


UPSTREAM_TASK = {
    "id":"1", "subject":"a",
    "status":"pending", "due":datetime.datetime(2001, 02, 03)}

TW_TASK_MANAGED = {"status":"pending", "description":"a", "uuid":"1",
            "project":"test", "due":"1234567890",}
TW_TASK_UNMANAGED = {"status":"completed", "description":"b", "project":"test"}

class TestTaskWarriorTask(object):
    def setup(self):
        self.factory = tasksync.TaskWarriorTaskFactory()

    # TODO: Need some kind of state transition methods.
    def test_status_mapping(self):
        task = self.factory.create_from(map=TW_TASK_MANAGED, project='test')
        task._source['status'] = 'pending'
        eq_(task.status, 'pending')
        ok_(task.is_pending)

        task._source['status'] = 'completed'
        eq_(task.status, 'completed')
        ok_(task.is_completed)

        task._source['status'] = 'deleted'
        eq_(task.status, 'deleted')
        ok_(task.is_deleted)

class TestTaskWarriorTaskFactory(object):
    def setup(self):
        self.factory = tasksync.TaskWarriorTaskFactory()

    def test_create_from_map(self):
        task = self.factory.create_from(map=TW_TASK_MANAGED, project='test')
        eq_(task.project, 'test')
        eq_(task.uid, '1')
        eq_(task.status, 'pending')
        eq_(task.subject, 'a')
        
    def test_create_from_other(self):
        source_task = MockUpstreamTask(**UPSTREAM_TASK)
        task = self.factory.create_from(other=source_task)
        eq_(task.status, 'pending')
        eq_(task.subject, 'a')
        eq_(task.uid, None)
        ok_(task.is_associated_with(source_task))

    def test_associate_with(self):
        upstream = MockUpstreamTask(provider='p', uid='u')
        task = self.factory.create_from(other=upstream)
        task.associate_with(upstream)
        ok_('tasksync_assoc_p' in task._source)
        ok_('tasksync_etag' in task._source)
        eq_(task.association, 'u')

    @raises(KeyError)
    def test_create_from_no_source(self):
        self.factory.create_from(project=None)


class TestTaskWarriorTaskRepository(object):
    def setup(self):
        self.db = mock()
        self.factory = tasksync.TaskWarriorTaskFactory()
        self.repository = tasksync.TaskWarriorTaskRepository(
                self.factory, db=self.db)

    def test_all_returns_all_lists(self):
        when(self.db).load_tasks().thenReturn(
                {'pending':[TW_TASK_MANAGED], 'completed':[TW_TASK_UNMANAGED]})
        eq_(len(self.repository.all()), 2)

    def test_save_inserts_unknown(self):
        when(self.db).task_add(**TW_TASK_UNMANAGED).thenReturn(TW_TASK_MANAGED)
        task = self.factory.create_from(map=TW_TASK_UNMANAGED)

        def cb(b, c):
            c._source['uuid'] = 1
            eq_(b._source, TW_TASK_MANAGED)

        batch = self.repository.batch_open();
        self.repository.save(task, batch, cb, task)
        self.repository.batch_close(batch)

        eq_(task.uid, 1) # updated in the callback (assert callback happens)

    def test_save_updates_known(self):
        task = self.factory.create_from(map=TW_TASK_MANAGED)
        task._source['uuid'] = '1'

        def cb(b, c):
            eq_(task, b)
            ok_(c)

        batch = self.repository.batch_open();
        self.repository.save(task, batch, cb, True)
        self.repository.batch_close(batch)

        verify(self.db).task_update(task._source)
