# Moved to management command

|||
| --- | --- |
| expire_downloads               | Had several issues. Functionality now runs automatically as part of `proc-download`.|
| group-delete                   | Delete a group  (delete_group.py)                                                   |
| group-move                     | Move a group to a different realm  (move_group.py)                                  |
| user-logout                    | Log user out of all sessions  (delete_sessions.py)                                  |
| user-delete                    | Delete a user (delete_user.py)                                                      |
| user-move                      | Moves a user to a different group (and possibly realm as well)  (move_user.py)      |

# Deleted: No longer needed
|||
| --- | --- |
| crontab                       | Replaced by Ashley's automated setup and documentation                                                                  |
| reload                        | No longer needed. Use systemd to restart EZID after changing settings                                                   |
| reload_all                    | "                                                                                                                       |
| validate_shoulders.py         | This validated the master shoulders text file, which we no longer use                                                   |
| show_version.sh               | EZID called out to this in order to get the git version, but we now get that from settings |

# Updated and verified working
| client.py                     | EZID command line client                                                                                              |

# Unchanged
## Many of these would be better as management commands
|||
| --- | --- |
| batch_register.py             | Batch registers identifiers                                                                                           |
| dashboard.py                  | Computes cumulative EZID statistics and uploads them to the CDL dashboard service                                     |
| decode_file.py                | Decodes a hex-encoded file                                                                                            |
| downserver.py                 | Standalone server that mimics EZID, but only indicates that the system is down                                        |
| batch_download.sh             | Issues a batch download request; downloads to a file in the current directory.                                        |
| link_check_emailer.py         | Emails link checker reports to all owners of identifiers whose check failures have reached the notification threshold |
| link_check_summary_report.py  | Creates a link checker summary report in the form of a CSV file                                                       |
| expunge.py                    | Expunges expired test identifiers                                                                                     |
| queue_admin.py                | Queue administration tool. Currently, works with the binder and DataCite queues only.                                 |
| shoulderless_identifiers.py   | Finds and counts all shoulderless identifiers, i.e., identifiers that are not extensions of current shoulders         |

# EZID dump file
## Unchanged, except renamed to group them
|||
| --- | --- |
| dump_binder.py                | Dumps a noid "egg" binder database                                            |
| dump_convert.py               | Convert EZID dump file from raw to normal (convert_dump.py)                   |
| dump_crossref.py              | Dumps all DOIs under one or more Crossref prefixes                            |
| dump_datacite.py              | Dumps DOIs belonging to one or more DataCite datacenters                      |
| dump_diff.py                  | Compares two dump files (diff_dumps.py)                                       |
| dump_diff_crossref.py         | Compares EZID DOI metadata with Crossref DOI metadata (diff_ezid_crossref.py) |
| dump_diff_datacite            | Compares EZID DOI metadata with DataCite DOI metadata (diff_ezid_datacite.py) |
| dump_diff_store_search        | Compares identifiers in the store and search databases (diff_store_search.py) |
| dump_filter.py                | Filter records in dump with a constraint expression (select.py)               |
| dump_idmap.sh                 | Extracts all agent identifiers from an EZID dump file (idmap)                 |
| dump_project.py               | Dump selected fields from those records (project.py)                          |
| dump_store.py                 | Dumps the store database to                                                   |

# Log files
|||
| --- | --- |
| filterlog.py                  | Reads EZID transaction log files, consolidates transaction BEGIN and END records |
| striplog.sh                   | Strips dated (i.e., already rolled over) EZID transaction log files              |

# New
|||
| --- | --- |
| diffsettings.sh               | Format the output of `./manage diffsettings` for readability      |
| generate_secret_key.py        | Generate a random string for use in the Django SECRET_KEY setting |
