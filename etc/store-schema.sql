-- ============================================================================
--
-- Store database schema.  The store database serves as a backup for
-- the primary "bind" noid database.  It also supports identifier
-- harvesting.
--
-- The 'identifier' table stores all identifiers and associated
-- metadata.  As in noid, identifier records are keyed by the
-- identifiers themselves (in the case of ARKs) or by the identifiers'
-- shadow ARKs (otherwise); identifiers are stored in scheme-less,
-- normalized form (e.g., "13030/foo").  Identifier owners are stored
-- as qualified, normalized ARK identifiers (e.g.,
-- "ark:/99166/p92z12p14").  For index efficiency the 'ownerMapping'
-- table maps identifier owners to local integer keys.  'updateTime'
-- is the maximum (i.e., the later) of the shadowed identifier's
-- update time (if applicable) and the ARK identifier's update time.
-- The metadata for an identifier is stored as a single line of text
-- that has been UTF-8 encoded and then gzipped.  The line uses the
-- space-separated format
--
--    label value label value ...
--
-- where field labels and values are encoded as they are in noid
-- (util.encode4 for labels and util.encode3 for values).  Note that
-- empty values will result in adjacent spaces in the line.  If
-- 'oaiVisible' is true, the identifier is visible in the OAI-PMH
-- feed.
--
-- Author:
--   Greg Janee <gjanee@ucop.edu>
--
-- License:
--   Copyright (c) 2013, Regents of the University of California
--   http://creativecommons.org/licenses/BSD/
--
-- ----------------------------------------------------------------------------

CREATE TABLE ownerMapping (
  ownerKey INTEGER NOT NULL PRIMARY KEY,
  owner TEXT NOT NULL UNIQUE
);

CREATE TABLE identifier (
  identifier TEXT NOT NULL PRIMARY KEY,
  ownerKey INTEGER NOT NULL REFERENCES ownerMapping,
  updateTime INTEGER NOT NULL,
  metadata BLOB NOT NULL,
  oaiVisible INTEGER NOT NULL -- boolean
);

CREATE INDEX identifierOwnerIndex ON identifier (ownerKey, identifier ASC);
CREATE INDEX identifierOaiIndex ON identifier (oaiVisible, updateTime ASC);

-- The following queue supports asynchronous identifier processing.
-- Identifiers are inserted intra-transaction by the 'store' module
-- and subsequently removed by the 'backproc' module as they are
-- processed.  'seq' defines the queue order.  'identifier' and
-- 'metadata' are as above.  'operation' is 0 (identifier created), 1
-- (updated), or 2 (deleted).  If 'updateExternalServices' is
-- true, the external services (DataCite, Crossref) are updated.

CREATE TABLE updateQueue (
  seq INTEGER PRIMARY KEY, -- implicit SQLite-style autoincrement
  identifier TEXT NOT NULL,
  metadata BLOB NOT NULL,
  operation INTEGER NOT NULL,
  updateExternalServices INTEGER NOT NULL DEFAULT 1 -- boolean
);
