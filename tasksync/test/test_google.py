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
import tasksync

from httplib2 import HttpLib2Error
from mockito import *
from nose.tools import raises, eq_, ok_

TASK_1 = {"status":"needsAction", "title":"Stuff", "id":"1", "etag":"1e",
        "kind":"tasks#task"}

class TestGoogleTask(object):
    def setup(self):
        self.factory = tasksync.GoogleTaskFactory()

    @raises(ValueError)
    def test_init_without_list_name(self):
        tasksync.GoogleTask({}, None)

    # FIXME: Need some kind of state transition methods.
    def test_status_mapping(self):
        task = tasksync.GoogleTask({}, 'foo')

        task._source['status'] = 'needsAction'
        eq_(task.status, 'pending')
        ok_(task.is_pending)

        task._source['status'] = 'completed'
        eq_(task.status, 'completed')
        ok_(task.is_completed)


class TestGoogleTaskFactory(object):
    def setup(self):
        self.factory = tasksync.GoogleTaskFactory()

    def test_create_from_map(self):
        task = self.factory.create_from('test', map=TASK_1)
        eq_(task.list_name, 'test')
        eq_(task.uid, '1')
        eq_(task.status, 'pending')
        eq_(task.subject, 'Stuff')
        eq_(task.etag, '1e')

    def test_create_from_other(self):
        task = self.factory.create_from('test', map=TASK_1)
        task = self.factory.create_from('test', other=task)
        eq_(task.list_name, 'test')
        eq_(task.status, 'pending')
        eq_(task.subject, 'Stuff')
        eq_(task.uid, None)
        eq_(task.etag, None)

    def test_create_from_other_passed_list_name_wins(self):
        task = self.factory.create_from('test', map=TASK_1)
        task = self.factory.create_from('test_overrides', other=task)
        eq_(task.list_name, 'test_overrides')

    def test_create_with_no_project_uses_default(self):
        task = self.factory.create_from('test', map=TASK_1)
        task = self.factory.create_from(other=task)
        eq_(task.list_name, '@default')

    @raises(KeyError)
    def test_create_from_without_valid_source(self):
        self.factory.create_from('list')


class TestGoogleTaskRepository(object):
    def setup(self):
        # Mock out the task lists (locally, list_names).
        self.factory = tasksync.GoogleTaskFactory()
        self.client = mock()

        list_name_home = {"kind": "tasks#taskList", "id":"1", "etag":"1",
                "title":"home", "updated":"2000-01-01T00:00:00.000Z",
                "selfLink":"http://example.com/home"}
        list_name_work = {"kind": "tasks#taskList", "id":"2", "etag":"2",
                "title":"work", "updated":"2000-01-01T00:00:00.000Z",
                "selfLink":"http://example.com/work"}
        list_names = {"kind":"tasks#taskLists", "etag":"a",
                "nextPageToken":"1", "items":[list_name_home, list_name_work]}
        tasklists = mock()
        when(self.client).tasklists(any()).thenReturn(tasklists)
        when(self.client).execute(tasklists).thenReturn(list_names)


        task_1 = {"status":"needsAction", "title":"Stuff", "id":"1",
                "etag":"1", "kind":"tasks#task"}
        task_2 = {"status":"completed", "title":"More stuff", "id":"2",
                "etag":"2", "kind":"tasks#task"}

        tasks_1 = {"kind":"tasks#tasks", "etag":"1",
                "nextPageToken":"1", "items":[task_1]}
        tasks_2 = {"kind":"tasks#tasks", "etag":"2",
                "nextPageToken":"2", "items":[task_2]}
        tasklist_1_tasks = mock()
        tasklist_2_tasks = mock()
        when(self.client).tasks(any()).thenReturn(tasklist_1_tasks)\
                .thenReturn(tasklist_2_tasks)
        when(self.client).execute(tasklist_1_tasks).thenReturn(tasks_1)
        when(self.client).execute(tasklist_2_tasks).thenReturn(tasks_2)
        self.repository = tasksync.GoogleTaskRepository(self.factory,
                client=self.client, task_list_filter=lambda t: True)

    def test_open_should_load_list_names(self):
        eq_(len(self.repository._task_lists), 2)

    def test_all_returns_all_lists(self):
        eq_(len(self.repository.all()), 2)

    def test_save_updates_known_to_batch(self):
        task = self.factory.create_from('home', map={'status':'needsAction'})
        task._source['id'] = '1'
        batch = {'count':0, 'batch':MockBatch()}
        self.repository.save(task, batch, None, None)
        # FIXME: This is wonky.
        verify(batch['batch'].delegate).add(any(), callback=any())

    def test_execute_batch(self):
        task = self.factory.create_from('home', map={'status':'needsAction'})
        batch = {'count':0, 'batch':MockBatch()}
        self.repository.save(task, batch, None, None)
        self.repository.batch_close(batch)
        verify(self.client, 2).execute(any())

    def test_execute_batch_with_no_adds(self):
        batch = {'count':0, 'batch':MockBatch()}
        self.repository.batch_close(batch)
        verifyZeroInteractions(batch['batch'].delegate)

class MockBatch(object):
    def __init__(self):
        self.delegate = mock()

    def add(self, batchable, callback=None):
        self.delegate.add(batchable, callback=callback)
