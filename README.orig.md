What is this thing?
===================

EZID is a Django web application that can be run under Django's built-in development server or under Apache with the mod_wsgi
extension.

Also included in this source distribution is a target URL link
checker, which runs as a separate process (and can run on a separate
machine from the main server) and is only loosely coupled to EZID
through EZID's database.  See
`.../SITE_ROOT/PROJECT_ROOT/tools/link-checker` for more information.
The remainder of this README discusses only the main server.

Prerequisites
=============

EZID requires:

- Django <http://www.djangoproject.com/> (version 1.8+; see below);
- Python <http://www.python.org/> (version 2.7+);
- a relational database (SQLite <http://www.sqlite.org/> and MySQL
  <http://www.mysql.com/> have both been used);
- if using MySQL, a MySQL API driver, e.g., mysqlclient
  <https://pypi.python.org/pypi/mysqlclient>;
- django-transaction-hooks <http://django-transaction-hooks.readthedocs.org/>
  (needed only until EZID has been migrated to Django 1.9);
- lxml <http://lxml.de/> for processing XML;
- Apache <http://httpd.apache.org/> if running under that, and if so,
- mod_wsgi <http://code.google.com/p/modwsgi/> (note that to work with
  mod_wsgi Python will have to have been compiled with shared object
  support).

Those are the core prerequisites for running EZID standalone.  But
EZID is of little value unless there are some other, external servers
running: a Noid <http://wiki.ucop.edu/display/Curation/NOID> "egg"
server for storing metadata (strictly speaking, optional, but an
essential component in the grand scheme of things); additional Noid
"nog" servers for minting identifiers; a shoulder server (optional);
DataCite services for creating DOI identifiers; and Crossref services
for registering with Crossref.

Caution: there may be dependencies on the specific version of Django:
certain files have been copied and in some cases modified from the
Django admin app's source code into the EZID repository.  Running
under a Django version different from that used during development may
cause problems.  See the READMEs in directories
.../SITE_ROOT/PROJECT_ROOT/static/admin and
.../SITE_ROOT/PROJECT_ROOT/templates/admin.

An additional prerequisite is Docutils
<http://docutils.sourceforge.net> for building the HTML version of the
API documentation.

General layout and configuration
================================

Whether it is run under the built-in development server or under
Apache, EZID assumes that it is embedded in the following directory
layout:

    .../SITE_ROOT/
        PROJECT_ROOT/
            (this software distribution:)
            LOCALIZATION
            NOTES
            README
            apache/
            code/
            doc/
            etc/
            ezidapp/
            profiles/
            settings/
                ezid.conf.shadow (not included in distribution)
            static/
            templates/
                info/ (separate distribution)
            tools/
            ui_tags/
            xsd/
        db/ (if using SQLite)
            search.sqlite3
            store.sqlite3
        download/
            public/
        logs/
            transaction_log

The names of the SITE_ROOT and PROJECT_ROOT directories are arbitrary
(EZID automatically detects what they are), but for the remainder of
this document we'll assume that they are literally those names.

EZID requires certain static HTML files to be present in the
.../SITE_ROOT/PROJECT_ROOT/templates/info directory.  These files are
provided by a separate Mercurial repository.

EZID requires one environment variable, DJANGO_SETTINGS_MODULE, that
indicates the deployment level.  Possible values:

    settings.localdev
    settings.remotedev
    settings.staging
    settings.production

See the corresponding modules in the settings directory for the
effects the deployment level has.  In addition, the deployment level
is used to define deployment-level-specific values for options in
.../SITE_ROOT/PROJECT_ROOT/settings/ezid.conf and
.../SITE_ROOT/PROJECT_ROOT/settings/ezid.conf.shadow, as in:

    [datacite]
    enabled: false
    {production}enabled: true

Running under Django
====================

When running EZID under Django's built-in server it will probably be
necessary to set the PYTHONPATH like so:

    setenv PYTHONPATH .../SITE_ROOT/PROJECT_ROOT

The combination of the PYTHONPATH and DJANGO_SETTINGS_MODULE
environment variables determines the location of the Django
application.

To run the built-in server:

    django-admin runserver

The server is hosted at http://localhost:8000/.

Initial setup
=============

To create the initial databases, assuming the above environment
variables have been set, and if EZID's "store" and "search" databases
are co-located in the same database instance (see Django setting
SEARCH_STORE_SAME_DATABASE), then:

    django-admin migrate

But if the store and search databases are different databases (whether
different architectures or simply different instances):

    django-admin migrate
    django-admin migrate --database=search

(Confusingly, for technical reasons the store database is to Django
the default database.)

If using MySQL:

    mysql < .../SITE_ROOT/PROJECT_ROOT/etc/store-mysql-addendum.sql
    mysql < .../SITE_ROOT/PROJECT_ROOT/etc/search-mysql-addendum.sql

To load initial data into the databases, run the following commands.
(The *.json files are stored in
.../SITE_ROOT/PROJECT_ROOT/ezidapp/fixtures, but the full path need
not be specified on the command line.)  An EZID administrator user and
group are required for the system to function, but otherwise the
users, groups, and realms defined in these file are just examples.

    django-admin loaddata store-init.json
    django-admin loaddata --database=search search-init.json

To give the EZID administrator account the password defined in the
.../SITE_ROOT/PROJECT_ROOT/settings/ezid.conf or
.../SITE_ROOT/PROJECT_ROOT/settings/ezid.conf.shadow file, do not use
Django's built-in 'createsuperuser' or 'changepassword' commands, but
instead:

    django-admin ezidadminsetpassword

Passwords for other accounts can be set using the admin interface.

Finally, to make the users and groups defined in these files fully
functional their persistent identifiers must be created, which is a
two-step process.  For each user and group, first create the
identifier using the command line client, e.g.:

    .../SITE_ROOT/PROJECT_ROOT/tools/client l admin:********
      create ark:/99166/p9g44hq02

Then visit the user's or group's page in the admin interface and click
"Save".

Running under Apache
====================

To run EZID under Apache and mod_wsgi, only the DJANGO_SETTINGS_MODULE
environment variable need be set.  Five sets of directives are
required in Apache's httpd.conf.  The following assume that EZID is
hosted at http://{host}/.

1. Load mod_wsgi.

    LoadModule wsgi_module path/to/mod_wsgi.so

2. Tell mod_wsgi to run EZID as a single, separate, multithreaded
process.  (Actually, this directive applies to all mod_wsgi
applications within the same server or virtual host.)  The name
"site-1" is arbitrary.

    WSGIDaemonProcess site-1 threads=50 shutdown-timeout=60

The parameters are not required, but may be desirable.  The default
number of threads is 15, which may be too low if clients submit many
requests concurrently.  The default shutdown timeout is 5 seconds; a
longer timeout gives current operations more time to finish cleanly.

3. Map EZID URLs to mod_wsgi+Django.

    WSGIScriptAlias / /path/to/SITE_ROOT/PROJECT_ROOT/apache/django.wsgi

4. Add the following directives.  If SSL is used to protect the login
page, the WSGIApplicationGroup directive is needed to avoid creating
two, parallel instances of the Python interpreter, one for HTTP and
one for HTTPS.  (Strangely, though, while this directive has the
desired effect, it does not need to be mentioned anywhere in Apache's
SSL configuration.  In fact, nothing EZID-related needs mentioning in
the SSL configuration.)  The WSGIPassAuthorization directive is needed
to pass through HTTP Basic authentication credentials (otherwise, they
get swallowed).

    <Directory /path/to/SITE_ROOT/PROJECT_ROOT/apache>
    Order Allow,Deny
    Allow from all
    WSGIApplicationGroup %{GLOBAL}
    WSGIProcessGroup site-1
    WSGIPassAuthorization on
    </Directory>

For somewhat mysterious reasons the application group *must* be
"%{GLOBAL}" and not an arbitrary name such as "ezid".  This is because
lxml is incompatible with mod_wsgi's use of Python sub-interpreters
(even though EZID is being run as a separate daemon process).

5. Add aliases so that static files are served by Apache, not Django.

    Alias /static /path/to/SITE_ROOT/PROJECT_ROOT/static

    <Directory /path/to/SITE_ROOT/PROJECT_ROOT/static>
    Order Allow,Deny
    Allow from all
    </Directory>

    Alias /download /path/to/SITE_ROOT/download/public

    <Directory /path/to/SITE_ROOT/download/public>
    Order Allow,Deny
    Allow from all
    Options -Indexes
    </Directory>

UI development setup
====================

Reqires:

- Node
- npm

CD to ezid repository root.

Install UI toolkit:

    npm install

To make changes to static elements, components, and
layouts:

    npm run ui:watch

This starts a local browser with the index page at
http://localhost:3000/, and will reload HTML, CSS, and JavaScript in
the browser immediately upon any changes to these files.

To create a build:

    npm run ui:build

This compiles CSS, JS and static webpages to [ezid repository root]/ui_library.

Copy the compiled HTML, CSS and JS from ui_library into their locations within the ezid app.
