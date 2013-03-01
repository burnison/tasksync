""" Provides a simple realization of Google Tasks. """

import httplib2
import oauth2client
import oauth2client.tools
import twgs

from datetime import datetime
from apiclient import discovery, http
from oauth2client.file import Storage
from twiggy import log


class GoogleTask(twgs.Task, twgs.UpstreamTask):
    """ Implementation for Google Tasks. """

    def __init__(self, source, project):
        super(GoogleTask, self).__init__()
        self._source = source
        self._project = project
        if self._project is None:
            raise ValueError("A project is required.")

    def copy_from(self, other):
        if other is None:
            raise ValueError("Cannot sync with nothing.")

        dfmt = self.__format_date # Format callback.
        self._project = other.project
        self._set_or_delete('title', other.subject)
        self._set_or_delete('due', other.due, fmt=dfmt)
        self._set_or_delete('completed', other.completed, fmt=dfmt)

    @property
    def should_sync(self):
        return True

    @property
    def provider(self):
        return 'googletasks'

    @property
    def uid(self):
        return self._source.get('id', None)

    @property
    def etag(self):
        return self._source.get('etag', None)

    @property
    def status(self):
        status = self._source['status']
        if status  == 'needsAction':
            return 'pending'
        elif status == 'completed':
            return 'completed'
        else:
            raise ValueError("Unknown status, %s" % status)

    @property
    def project(self):
        return self._project

    @property
    def subject(self):
        return self._source.get('title', None)

    @property
    def due(self):
        return self.__parse_date(self._source.get('due', None))

    @property
    def completed(self):
        return self.__parse_date(self._source.get('completed', None))


    def __parse_date(self, as_string):
        #pylint: disable=R0201,C0111
        """ Parse the specified date. """
        if as_string is None:
            return None
        return datetime.strptime(as_string, '%Y-%m-%dT%H:%M:%S.%fZ')

    def __format_date(self, iso_date):
        #pylint: disable=R0201,C0111
        return datetime.strftime(iso_date, '%Y-%m-%dT%H:%M:%S.000Z')

class GoogleTaskFactory(twgs.TaskFactory):
    def create_from(self, **kwargs):
        """ Create a new task from another task, 'other', or a map, 'map'. """
        if 'map' in kwargs:
            if 'project' not in kwargs:
                raise KeyError("A project must be provided.")
            else:
                return self._create_from_map(kwargs['map'].copy(),
                        kwargs['project'])

        elif 'other' in kwargs:
            project = kwargs.get('project', None)
            return self._create_from_other(kwargs['other'], project)

        else:
            raise KeyError('Either a map or task argument must be provided.')

    def _create_from_map(self, source, project):
        return GoogleTask(source, project)

    def _create_from_other(self, other, project):
        #pylint: disable=W0212
        status = 'needsAction' if other.status == 'pending' else 'completed'
        task = GoogleTask({'status':status}, project=other.project)
        task.copy_from(other)
        task._project = project or other.project
        return task

class GoogleTaskRepository(twgs.TaskRepository):
    def __init__(self, factory, client=None, **kwargs):
        self._factory = factory
        self._client = client or ApiClient(**kwargs)
        self._projects = self.__load_projects()

    def batch_create(self):
        return http.BatchHttpRequest()

    def batch_close(self, batch):
        self._client.execute(batch)

    def all(self):
        tasks = []
        for project in self._projects.keys():
            log.info("Retrieving tasks for {0}.", project)

            method = lambda s: s.list(tasklist=self._projects[project])
            upstream_tasks = self._client.tasks(method)
            upstream_tasks = self._client.execute(upstream_tasks)
            if 'items' in upstream_tasks:
                tasks += [self._factory.create_from(map=t, project=project)
                        for t in upstream_tasks['items']
                        if t['title'] != '']
        return tasks

    def delete(self, gtask, batch, cb=None):
        tasklist = self._projects[gtask.project]
        def method(service):
            action = service.delete(task=gtask.uid, tasklist=tasklist)
            batch.add(action, callback=cb)
        self._client.tasks(method)

    def save(self, gtask, batch, userdata=None, cb=None):
        tasklist = self._projects[gtask.project]
        def method(service):
            action = None
            if gtask.uid is None:
                action = service.insert(tasklist=tasklist, body=gtask._source)
            else:
                action = service.update(tasklist=tasklist, body=gtask._source,
                        task=gtask.uid)
            return action

        action = self._client.tasks(method)
        batch.add(action, callback=self.__batch_cb(gtask, userdata, cb))

    def __load_projects(self):
        projects = {}
        lists = self._client.tasklists(lambda s: s.list())
        lists = self._client.execute(lists)
        for p in lists['items']:
            projects[p['title']] = p['id']
        return projects

    def __batch_cb(self, gtask, userdata, cb):
        def impl(request_id, response, exception):
            if not exception is None:
                log.error("Couldn't sync {0} ({1}): {2}",
                        request_id, exception, exception)
                return
            gtask._source = response
            if not cb is None:
                cb(gtask, userdata)
        return impl

class ApiClient(object):
    """ Wrapper around Google Task API. """
    def __init__(self, **kwargs):
        credentials = self._authenticate(**kwargs)
        self._http = credentials.authorize(httplib2.Http())
        self._service = discovery.build(
                serviceName='tasks', version='v1', http=self._http)

    def _authenticate(self, **kwargs):
        """ Get the auth token. """
        flow = oauth2client.client.OAuth2WebServerFlow(
                client_id=kwargs['client_id'],
                client_secret=kwargs['client_secret'],
                scope='https://www.googleapis.com/auth/tasks',
                user_agent='tasksync/1.0')

        storage = Storage(kwargs['credential_storage'])
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            credentials = oauth2client.tools.run(flow, storage)
        return credentials

    def tasklists(self, method):
        return method(self._service.tasklists())

    def tasks(self, method):
        return method(self._service.tasks())

    def execute(self, executable):
        if executable is None:
            return None
        return executable.execute(http=self._http)
