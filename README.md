tasksync
========

tasksync is a CLI tool to sync tasks between task trackers offered on an as-is
basis. The project is in a relatively crude state and makes several assumptions
about the end-user (namely: they're comfortable with programming).

tasksync was originally developed for, and has been tested with, task syncing
between TaskWarrior and Google tasks. Other implementations may be supported at
a future date.

Pull requests are absolutely welcome on this project, especially if they make
the project more user-friendly.


Usage
-----

Configure executions within config.py and run run tasksync from console. As
always, be sure you have up-to-date backups in the event anything goes wrong.

When syncing against Google Tasks, an OAuth token will be required. Upon first
execution, you will be prompted, by Google, to authenticate and grant tasksync
permission to access your Google Tasks data. Be sure to check the URL, as
tasksync relies on third-party libraries to perform OAuth authentication.

An example `config.py` file has been included as an example of what can be done,
and callbacks can be stacked to really customize the import/export steps.


