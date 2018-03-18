# tasksync

tasksync is a CLI tool to sync tasks between task trackers offered on an as-is
basis. The project is in a relatively crude state and makes several assumptions
about the end-user (namely: he or she is comfortable with programming).

tasksync was originally developed for, and has been tested with, task syncing
between TaskWarrior and Google Tasks. Other implementations may be supported at
a future date.

Pull requests are absolutely welcome on this project, especially if they make
the project more user-friendly.

## Installation

In the current state of the project, you're encouraged to run out of a [virtual
environment](https://virtualenv.pypa.io/en/stable/):

1. `git clone https://github.com/burnison/tasksync`
1. `cd tasksync`
1. `virtualenv .venv`
1. `. .venv/bin/activate`
1. `python setup.py install`

And, to use:

1. `CLIENT_ID='xyz' CLIENT_SECRET='abc' python tasksync --help`

Take care to protect your `CLIENT_SECRET`.


### Configuration

To keep the utmost amount of flexibility, configuration is done through the
`config.py`. This means a certain number of assumptions have been made about the
user, specifically that he or she is comfortable with python programming. To
configure,

1. As always, be sure you have up-to-date backups of everything in the event
   anything goes wrong.
1. Copy the provided `config.py.example` file to `config.py`.
1. Make whatever necessary changes to `config.py` (see _Rough Design_).


### Notes about Google

When syncing against Google Tasks, an OAuth token will be required. You can
create one using the [Google Cloud Console](https://console.cloud.google.com).

Upon first execution, you will be prompted, by Google, to authenticate and grant
`tasksync` permission to access your Google Tasks data. Be sure to check the
URL, as `tasksync` relies on third-party libraries to perform OAuth
authentication.


#### Rough design

Each synchronisation is an `execution`, provided by `config.executions`. In the
provided example, `tw2gt` is an example on how you can synchronize Google Tasks
with TaskWarrior.

Each execution contains an `upstream` and `downstream` source. In the provided
example, `upstream` is Google Tasks, and `downstream` is TaskWarrior. Each
source or sink contains a

* `TaskFactory`, which knows how to create `Task` objects from the underlying
  provider.
* `Repository`, which understands the wire level definition of a `Task`.
* `Filter`, which allows tasks to be excluded from the sync.
* `Callback`, which allows tasks to be fluffed, changed, rewritten, etc. during
  the sync.
* a decision whether or not "orphaned" tasks should be deleted. Orphaned tasks
  are those that have a bidirectional association to a task not present in the
  other system.

Additional providers can be added by the same mechanism, "simply" by extending
the `TaskFactory`, `TaskRepository`, and `Task` classes.


## Yep, this project is rough

As noted several times in this readme, enhancements are welcome. One day, I plan
to add a CalDAV/TaskDAV provider. One day. That's my top priority.
