#pylint: disable=C0103,C0111,I0011,I0012,W0704,W0142,W0212,W0232,W0613,W0702
#pylint: disable=R0201,W0614,R0914,R0912,R0915,R0913,R0904,R0801,W0201,R0902
import twgs
from httplib2 import HttpLib2Error
from mockito import *
from nose.tools import raises, eq_, ok_

TASK_1 = {"status":"needsAction", "title":"Stuff", "id":"1", "etag":"1e",
        "kind":"tasks#task"}

class TestGoogleTask(object):
    def setup(self):
        self.factory = twgs.GoogleTaskFactory()

    @raises(ValueError)
    def test_init_without_project(self):
        twgs.GoogleTask({}, None)

    # FIXME: Need some kind of state transition methods.
    def test_status_mapping(self):
        task = twgs.GoogleTask({}, 'foo')

        task._source['status'] = 'needsAction'
        eq_(task.status, 'pending')
        ok_(task.is_pending)

        task._source['status'] = 'completed'
        eq_(task.status, 'completed')
        ok_(task.is_completed)


class TestGoogleTaskFactory(object):
    def setup(self):
        self.factory = twgs.GoogleTaskFactory()

    def test_create_from_map(self):
        task = self.factory.create_from(map=TASK_1, project='test')
        eq_(task.project, 'test')
        eq_(task.uid, '1')
        eq_(task.status, 'pending')
        eq_(task.subject, 'Stuff')
        eq_(task.etag, '1e')

    @raises(ValueError)
    def test_create_from_map_without_project(self):
        self.factory.create_from(map=TASK_1, project=None)

    def test_create_from_other(self):
        task = self.factory.create_from(map=TASK_1, project='test')
        task = self.factory.create_from(other=task)
        eq_(task.project, 'test')
        eq_(task.status, 'pending')
        eq_(task.subject, 'Stuff')
        eq_(task.uid, None)
        eq_(task.etag, None)

    def test_create_from_other_without_project(self):
        task = self.factory.create_from(map=TASK_1, project='test')
        task = self.factory.create_from(other=task, project='test_overrides')
        eq_(task.project, 'test_overrides')

    @raises(KeyError)
    def test_create_from_without_valid_source(self):
        self.factory.create_from(project=None)


class TestGoogleTaskRepository(object):
    def setup(self):
        # Mock out the task lists (locally, projects).
        self.factory = twgs.GoogleTaskFactory()

        project_home = {"kind": "tasks#taskList", "id":"1", "etag":"1",
                "title":"home", "updated":"2000-01-01T00:00:00.000Z",
                "selfLink":"http://example.com/home"}
        project_work = {"kind": "tasks#taskList", "id":"2", "etag":"2",
                "title":"work", "updated":"2000-01-01T00:00:00.000Z",
                "selfLink":"http://example.com/work"}
        projects = {"kind":"tasks#taskLists", "etag":"a",
                "nextPageToken":"1", "items":[project_home, project_work]}
        client = mock()
        tasklists = mock()
        when(client).tasklists(any()).thenReturn(tasklists)
        when(client).execute(tasklists).thenReturn(projects)


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
        when(client).tasks(any()).thenReturn(tasklist_1_tasks)\
                .thenReturn(tasklist_2_tasks)
        when(client).execute(tasklist_1_tasks).thenReturn(tasks_1)
        when(client).execute(tasklist_2_tasks).thenReturn(tasks_2)
        self.repository = twgs.GoogleTaskRepository(self.factory, client=client)


    def test_open_should_load_projects(self):
        eq_(len(self.repository._projects), 2)

    def test_all_returns_all_lists(self):
        eq_(len(self.repository.all()), 2)

    @raises(KeyError)
    def test_save_fails_when_unknown_project_is_specified(self):
        task = self.factory.create_from(map={'status':'needsAction'},project='flub')
        self.repository.save(task, mock())

    def test_save_inserts_unknown_to_batch(self):
        batch = mock()
        task = self.factory.create_from(map={'status':'needsAction'},project='home')
        self.repository.save(task, batch)
        verify(batch).add(any(), callback=any())

    def test_save_updates_known_to_batch(self):
        batch = mock()
        task = self.factory.create_from(map={'status':'needsAction'},project='home')
        task._source['id'] = '1'
        self.repository.save(task, batch)
        verify(batch).add(any(), callback=any())
