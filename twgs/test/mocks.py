#pylint: disable=C0103,C0111,I0011,I0012,W0704,W0142,W0212,W0232,W0613,W0702
#pylint: disable=R0201,W0614,R0914,R0912,R0915,R0913,R0904,R0801,W0201,R0902
import twgs

class MockTask(twgs.Task):
    def __init__(self, **kwargs):
        self._uid = kwargs.get('uid', None)
        self._status = kwargs.get('status', None)
        self._project = kwargs.get('project', None)
        self._subject = kwargs.get('subject', None)
        self._completed = kwargs.get('completed', None)
        self._due = kwargs.get('due', None)
        self._provider = kwargs.get('provider', None)
        self._etag = kwargs.get('etag', None)

    @property
    def should_sync(self):
        return True

    @property
    def uid(self):
        return self._uid

    @property
    def status(self):
        return self._status

    @property
    def project(self):
        return self._project

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
        pass

class MockDownstreamTask(MockTask, twgs.DownstreamTask):
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

class MockUpstreamTask(MockTask, twgs.UpstreamTask):
    def __init__(self, **kwargs):
        super(MockUpstreamTask, self).__init__(**kwargs)
        self._provider = kwargs.get('provider', None)
        self._etag = kwargs.get('etag', None)

    @property
    def provider(self):
        return self._provider

    @property
    def etag(self):
        return self._etag
