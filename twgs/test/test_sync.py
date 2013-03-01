#pylint: disable=C0103,C0111,I0011,I0012,W0704,W0142,W0212,W0232,W0613,W0702
#pylint: disable=R0201,W0614,R0914,R0912,R0915,R0913,R0904,R0801,W0201,R0902
import twgs

from mocks import MockUpstreamTask, MockDownstreamTask
from mockito import mock, when, verify, verifyZeroInteractions, any
from nose.tools import raises, eq_, ok_

class TestSync(object):
    def setup(self):
        self.upstream = []
        self.downstream = []
        for _ in range(0, 5):
            self.upstream.append(MockUpstreamTask(subject='a',provider='g',uid='a'))
            self.downstream.append(MockDownstreamTask(subject='b'))

        self.upstream_factory = mock(twgs.TaskFactory)
        self.downstream_factory = mock(twgs.TaskFactory)
        self.upstream_repo = mock(twgs.TaskRepository)
        self.downstream_repo = mock(twgs.TaskRepository)

    def _do_sync_all(self):
        """ Clean up the call. """
        twgs.sync_all(self.downstream_repo, self.downstream_factory,
                self.upstream_repo, self.upstream_factory)

    def test_no_tasks(self):
        when(self.downstream_repo).all().thenReturn([])
        when(self.upstream_repo).all().thenReturn([])

        self._do_sync_all()

        verify(self.downstream_repo, 0).save(any())
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())

    def test_unknown_from_downstream(self):
        d = self.downstream[0]
        u = self.upstream[0]
        when(self.downstream_repo).all().thenReturn([d])
        when(self.upstream_repo).all().thenReturn([])
        when(self.upstream_factory).create_from(other=d).thenReturn(u)

        self._do_sync_all()

        verify(self.upstream_repo).save(
                u, batch=any(), userdata=any(), cb=any())

    def test_known_from_downstream_not_stale(self):
        d = self.downstream[0]
        u = self.upstream[0]
        d.associate_with(u)
        when(self.downstream_repo).all().thenReturn([d])
        when(self.upstream_repo).all().thenReturn([u])

        self._do_sync_all()

        verify(self.downstream_repo, 0).save(any())
        verify(self.upstream_repo).save(
                u, batch=any(), userdata=any(), cb=any())

    def test_known_from_downstream_stale(self):
        d = self.downstream[0]
        u = self.upstream[0]
        d.associate_with(u)
        d.mark_dirty()
        when(self.downstream_repo).all().thenReturn([d])
        when(self.upstream_repo).all().thenReturn([u])

        self._do_sync_all()

        verify(self.downstream_repo).save(d)
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())

    def test_known_from_upstream(self):
        d = self.downstream[0]
        u = self.upstream[0]
        d.associate_with(u)
        d.mark_dirty()
        when(self.downstream_repo).all().thenReturn([d])
        when(self.upstream_repo).all().thenReturn([u])

        self._do_sync_all()

        verify(self.downstream_repo).save(d)
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())

    def test_unknown_from_upstream(self):
        d = self.downstream[0]
        u = self.upstream[0]
        when(self.downstream_repo).all().thenReturn([])
        when(self.upstream_repo).all().thenReturn([u])
        when(self.downstream_factory).create_from(other=u).thenReturn(d)

        self._do_sync_all()

        verify(self.downstream_repo).save(d)
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())

    def test_known_deleted_from_upstream(self):
        d = self.downstream[0]
        d.associate_with(self.upstream[0])
        when(self.downstream_repo).all().thenReturn([d])
        when(self.upstream_repo).all().thenReturn([])

        self._do_sync_all()

        verify(self.downstream_repo).delete(d)
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())
