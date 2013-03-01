#pylint: disable=C0103,C0111,I0011,I0012,W0704,W0142,W0212,W0232,W0613,W0702
#pylint: disable=R0201,W0614,R0914,R0912,R0915,R0913,R0904,R0801,W0201,R0902
import twgs

from mocks import MockUpstreamTask
from mockito import mock, when, verify, any
from nose.tools import raises, eq_, ok_

TASK_1 = {"status":"pending", "description":"a", "uuid":"1",
            "project":"test", "due":"1234567890",}
TASK_2 = {"status":"completed", "description":"b", "project":"test"}

class TestTaskWarriorTask(object):
    def setup(self):
        self.factory = twgs.TaskWarriorTaskFactory()

    # TODO: Need some kind of state transition methods.
    def test_status_mapping(self):
        task = self.factory.create_from(map=TASK_1, project='test')
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
        self.factory = twgs.TaskWarriorTaskFactory()

    def test_create_from_map(self):
        task = self.factory.create_from(map=TASK_1, project='test')
        eq_(task.project, 'test')
        eq_(task.uid, '1')
        eq_(task.status, 'pending')
        eq_(task.subject, 'a')
        
    def test_create_from_other(self):
        task = self.factory.create_from(map=TASK_1)
        task = self.factory.create_from(other=task)
        eq_(task.project, 'test')
        eq_(task.status, 'pending')
        eq_(task.subject, 'a')
        eq_(task.uid, None)

    def test_associate_with(self):
        upstream = MockUpstreamTask(provider='p', uid='u')
        task = self.factory.create_from(other=upstream)
        task.associate_with(upstream)
        ok_('twgs_assoc_p' in task._source)
        ok_('twgs_etag' in task._source)
        eq_(task.association, 'u')

    @raises(KeyError)
    def test_create_from_no_source(self):
        self.factory.create_from(project=None)


class TestTaskWarriorTaskRepository(object):
    def setup(self):
        self.db = mock()
        self.factory = twgs.TaskWarriorTaskFactory()
        self.repository = twgs.TaskWarriorTaskRepository(
                self.factory, db=self.db)

    def test_all_returns_all_lists(self):
        when(self.db).load_tasks().thenReturn(
                {'pending':[TASK_1], 'completed':[TASK_2]})
        eq_(len(self.repository.all()), 2)

    def test_save_inserts_unknown(self):
        when(self.db).task_add(**TASK_2).thenReturn(TASK_1)
        task = self.factory.create_from(map=TASK_2)
        self.repository.save(task)
        eq_(task._source, TASK_1)

    def test_save_updates_known(self):
        task = self.factory.create_from(map=TASK_1)
        task._source['id'] = '1'
        self.repository.save(task,)
        verify(self.db).task_update(any())
