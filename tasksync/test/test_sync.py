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

        self.upstream_factory = mock(tasksync.TaskFactory)
        self.downstream_factory = mock(tasksync.TaskFactory)
        self.upstream_repo = mock(tasksync.TaskRepository)
        self.downstream_repo = mock(tasksync.TaskRepository)
        self.execution = {
            'upstream':{
                'repository':self.upstream_repo,
                'factory':self.upstream_factory,
                'delete_orphans':False,
                'cb':lambda d, u: True},
            'downstream':{
                'repository':self.downstream_repo,
                'factory':self.downstream_factory,
                'delete_orphans':False,
                'cb':lambda u, d: True}
        };

    def _do_sync_all(self):
        """ Clean up the call. """
        tasksync.sync_all(self.execution)

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

        verify(self.downstream_repo, 0).save(any())
        verify(self.upstream_repo).save(
                u, batch=any(), userdata=any(), cb=any())

    def test_unknown_from_downstream_filter_drop(self):
        when(self.downstream_repo).all().thenReturn([self.downstream[0]])
        when(self.upstream_repo).all().thenReturn([])

        self.execution['upstream']['cb'] = lambda d, u: False
        self._do_sync_all()

        verify(self.downstream_repo, 0).save(any())
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())

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

    def test_unknown_from_upstream_filter_drop(self):
        d = self.downstream[0]
        u = self.upstream[0]
        when(self.downstream_repo).all().thenReturn([])
        when(self.upstream_repo).all().thenReturn([u])
        # This one is needed because downstream calls associate()
        when(self.downstream_factory).create_from(other=u).thenReturn(d)

        self.execution['downstream']['cb'] = lambda u, d: False
        self._do_sync_all()

        verify(self.downstream_repo, 0).save(any())
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())

    def test_known_deleted_from_upstream_with_orphan_removal(self):
        d = self.downstream[0]
        d.associate_with(self.upstream[0])
        when(self.downstream_repo).all().thenReturn([d])
        when(self.upstream_repo).all().thenReturn([])

        self.execution['downstream']['delete_orphans'] = True
        self._do_sync_all()

        verify(self.downstream_repo).delete(d)
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())

    def test_known_deleted_from_upstream_no_orphan_removal(self):
        d = self.downstream[0]
        d.associate_with(self.upstream[0])
        when(self.downstream_repo).all().thenReturn([d])
        when(self.upstream_repo).all().thenReturn([])

        self._do_sync_all()

        verify(self.downstream_repo, 0).delete(d)
        verify(self.upstream_repo, 0).save(
                any(), batch=any(), userdata=any(), cb=any())
