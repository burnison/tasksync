tasksync
========

tasksync is a CLI tool to sync tasks between task trackers.

tasksync was originally developed for, and has been tested with, task syncing
between TaskWarrior and Google tasks. Other implementations may be supported at
a future date.

tasksync is developed by Richard Burnison and is offered under the GNU GPL 3
license.


Installation
------------

tasksync has several dependencies on Python 2, and thus, is only functional under
Python 2.7. As upstream dependencies change, so will tasksync.


Usage
-----

Configure executions within config.py and run run tasksync from console. As
always, be sure you have up-to-date backups in the event anything goes wrong.

When syncing against Google Tasks, an OAuth token will be required. Upon first
execution, you will be prompted, by Google, to authenticate and grant tasksync
permission to access your Google Tasks data. Be sure to check the URL, as
tasksync relies on third-party libraries to perform OAuth authentication.
