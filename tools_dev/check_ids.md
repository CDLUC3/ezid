
# dev-check-ids

Annotate a stream of identifiers with associated metadata and misc housekeeping information pulled from an EZID database.

### Input and output

Input can be stdin, pipes, files or a combination of those. Each source of input should provide one or more identifiers as minted by EZID. The identifiers should each be on a separate line. Blank lines are ignored.
 
Output is always stdout and stderr. Both successful annotations and error messages are written to stdout. Only status and progress messages are written to stderr.

### Secure handling of database login credentials

Database credentials and related connection details are stored in an encrypted configuration file, `~/.mylogin.cnf`, which is the preferred location in which to store database credentials in later versions MySQL.

Add all the options required to connect to an EZID database, using the `mysql_config_editor` command. E.g.,

```shell
$ mysql_config_editor set --login-path=ezid-test-db --host=server.com --user=ezidro --password

* Type the password when prompted. Avoid passing the password as a command line argument.
```

To print all connection details currently stored in the `~/.mylogin.cnf` file (passwords are not shown):

```shell
$ mysql_config_editor print --all
```

See the man pages for `mysql_config_editor`, `mysql` and other bundled commands for more information about the options and for how to perform various maintenance related tasks.

A port or socket can also be be specified if the service is not listening on the standard port of 3306.

The new connection can now be used by `check-ids.py`, which takes the database schema name that was specified with `--login-path` as a required first parameter. E.g.,

```shell
$ check-ids.py ezid-test-db ids1.txt <(xzcat ids2.xz) <ids3-named-pipe | tee all-results.txt
```

To use thew new connection from the `mysql` command line client, pass the database name using the `--login-path` parameter. E.g.,

```shell
$ mysql --login-path=ezid-test-db
```
