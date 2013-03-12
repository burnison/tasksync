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

""" Provides a simple realization of Google Tasks. """

import httplib2
import oauth2client
import oauth2client.tools
import tasksync

from datetime import datetime
from apiclient import discovery, http
from oauth2client.file import Storage
from twiggy import log


class GoogleTask(tasksync.Task, tasksync.UpstreamTask):
    """ Implementation for Google Tasks. """

    def __init__(self, source, list_name):
        if list_name is None:
            raise ValueError("A list name is required.")

        super(GoogleTask, self).__init__()
        self._source = source
        self.list_name = list_name

    def __str__(self):
        return "%s[id=%s,l=%s,s=%s]" % (
                'GoogleTask', self.uid, self.list_name, self.subject)

    def copy_from(self, other):
        if other is None:
            raise ValueError("Cannot sync with nothing.")

        self.list_name = getattr(other, 'list_name', self.list_name)
        self.__set_or_delete('title', other.subject)

        dfmt = self.__format_date # Format callback.
        self.__set_or_delete('due', other.due, fmt=dfmt)
        self.__set_or_delete('completed', other.completed, fmt=dfmt)

        if other.is_completed:
            self._source['status'] = 'completed'

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

    def __set_or_delete(self, key, value, fmt=None):
        if value is None:
            if key in self._source:
                del self._source[key]
        else:
            if not fmt is None:
                value = fmt(value)
            self._source[key] = value

class GoogleTaskFactory(tasksync.TaskFactory):
    def create_from(self, list_name='@default', **kwargs):
        """
        Create a new task from another task, 'other', or a map, 'map'.
        In all cases, the provided task_list will be assigned to the
        new instance.
        """
        if 'map' in kwargs:
            return GoogleTask(kwargs['map'].copy(), list_name)
        elif 'other' in kwargs:
            return self._create_from_other(kwargs['other'], list_name)
        else:
            raise KeyError('Either a map or task argument must be provided.')

        return 

    def _create_from_other(self, other, list_name):
        status = 'needsAction' if other.status == 'pending' else 'completed'
        task = GoogleTask({'status':status}, list_name)
        task.copy_from(other)
        task.list_name = list_name
        return task

class GoogleTaskRepository(tasksync.TaskRepository):
    def __init__(self, factory, client=None, **kwargs):
        self._factory = factory
        self._client = client or ApiClient(**kwargs)
        self._task_lists = self.__load_task_lists(kwargs['task_list_filter'])

    def batch_create(self):
        return {'count':0, 'batch':http.BatchHttpRequest()}

    def batch_close(self, batch):
        if batch['count'] > 0:
            self._client.execute(batch['batch'])

    def all(self):
        tasks = []
        for task_list in self._task_lists.keys():
            log.debug("Retrieving tasks for {0}.", task_list)

            method = lambda s: s.list(tasklist=self._task_lists[task_list])
            upstream_tasks = self._client.tasks(method)
            upstream_tasks = self._client.execute(upstream_tasks)
            if 'items' in upstream_tasks:
                tasks += [self._factory.create_from(task_list, map=t)
                        for t in upstream_tasks['items']
                        if t['title'] != '']
        return tasks

    def delete(self, gtask, batch, cb=None):
        tasklist = self._task_lists[gtask.list_name]
        def method(service):
            action = service.delete(task=gtask.uid, tasklist=tasklist)
            batch['batch'].add(action, callback=cb)
            batch['count'] += 1
        self._client.tasks(method)

    def save(self, gtask, batch, userdata=None, cb=None):
        tasklist = self._task_lists.get(gtask.list_name, '@default')
        def method(service):
            action = None
            if gtask.uid is None:
                action = service.insert(tasklist=tasklist, body=gtask._source)
            else:
                action = service.update(tasklist=tasklist, body=gtask._source,
                        task=gtask.uid)
            return action

        action = self._client.tasks(method)
        batch['batch'].add(action, callback=self.__batch_cb(gtask, userdata, cb))
        batch['count'] += 1

    def __load_task_lists(self, task_list_filter):
        lists = self._client.tasklists(lambda s: s.list())
        lists = self._client.execute(lists)
        return {p['title']:p['id']
                for p in lists['items']
                if task_list_filter(p['title'])}

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
