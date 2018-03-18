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
from .mocks import MockUpstreamTask

from mockito import mock, when, verify, any
from tasksync.taskwarrior import TaskWarriorTaskFactory, TaskWarriorTaskRepository

import datetime
import unittest


UPSTREAM_TASK = {
    "id":"1", "subject":"a",
    "status":"pending", "due":datetime.datetime(2001, 2, 3)}

TW_TASK_MANAGED = {"status":"pending", "description":"a", "uuid":"1",
            "project":"test", "due":"1234567890",}
TW_TASK_UNMANAGED = {"status":"completed", "description":"b", "project":"test"}

class TestTaskWarriorTask(unittest.TestCase):
    def setUp(self):
        self.factory = TaskWarriorTaskFactory()

    # TODO: Need some kind of state transition methods.
    def test_status_mapping(self):
        task = self.factory.create_from(map=TW_TASK_MANAGED, project='test')
        task._source['status'] = 'pending'
        self.assertEqual(task.status, 'pending')
        self.assertTrue(task.is_pending)

        task._source['status'] = 'completed'
        self.assertEqual(task.status, 'completed')
        self.assertTrue(task.is_completed)

        task._source['status'] = 'deleted'
        self.assertEqual(task.status, 'deleted')
        self.assertTrue(task.is_deleted)

class TestTaskWarriorTaskFactory(unittest.TestCase):
    def setUp(self):
        self.factory = TaskWarriorTaskFactory()

    def test_create_from_map(self):
        task = self.factory.create_from(map=TW_TASK_MANAGED, project='test')
        self.assertEqual(task.project, 'test')
        self.assertEqual(task.uid, '1')
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.subject, 'a')

    def test_create_from_other(self):
        source_task = MockUpstreamTask(**UPSTREAM_TASK)
        task = self.factory.create_from(other=source_task)
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.subject, 'a')
        self.assertEqual(task.uid, None)
        self.assertTrue(task.is_associated_with(source_task))

    def test_associate_with(self):
        upstream = MockUpstreamTask(provider='p', uid='u')
        task = self.factory.create_from(other=upstream)
        task.associate_with(upstream)
        self.assertTrue('tasksync_assoc_p' in task._source)
        self.assertTrue('tasksync_etag' in task._source)
        self.assertEqual(task.association, 'u')

    def test_create_from_no_source(self):
        with self.assertRaises(KeyError):
            self.factory.create_from(project=None)


class TestTaskWarriorTaskRepository(unittest.TestCase):
    def setUp(self):
        self.db = mock()
        self.factory = TaskWarriorTaskFactory()
        self.repository = TaskWarriorTaskRepository(
                self.factory, db=self.db)

    def test_all_returns_all_lists(self):
        when(self.db).load_tasks().thenReturn(
                {'pending':[TW_TASK_MANAGED], 'completed':[TW_TASK_UNMANAGED]})
        self.assertEqual(len(self.repository.all()), 2)

    def test_save_inserts_unknown(self):
        when(self.db).task_add(**TW_TASK_UNMANAGED).thenReturn(TW_TASK_MANAGED)
        task = self.factory.create_from(map=TW_TASK_UNMANAGED)

        def cb(b, c):
            c._source['uuid'] = 1
            self.assertEqual(b._source, TW_TASK_MANAGED)

        batch = self.repository.batch_open();
        self.repository.save(task, batch, cb, task)
        self.repository.batch_close(batch)

        self.assertEqual(task.uid, 1) # updated in the callback (assert callback happens)

    def test_save_updates_known(self):
        task = self.factory.create_from(map=TW_TASK_MANAGED)
        task._source['uuid'] = '1'

        def cb(b, c):
            self.assertEqual(task, b)
            self.assertTrue(c)

        batch = self.repository.batch_open();
        self.repository.save(task, batch, cb, True)
        self.repository.batch_close(batch)

        verify(self.db).task_update(task._source)
