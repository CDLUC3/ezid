-- ============================================================================
--
-- Search database schema.
--
-- The 'identifier' table stores all identifiers, not including shadow
-- ARKs.  Identifiers themselves are stored in qualified, normalized
-- form (e.g., "ark:/13030/foo").  Identifier attributes are not
-- encoded.  Owners and co-owners are stored as ARK identifiers (e.g.,
-- "ark:/99166/p92z12p14").
--
-- To support searching by owner, the 'ownership' table relates owners
-- and identifier-level co-owners to identifiers.  Thus, if identifier
-- I has owner A and co-owners B and C, the table will hold tuples
-- (A,I), (B,I), and (C,I).  Note that this table doesn't account for
-- ownership via account-level co-ownership.
--
-- Author:
--   Greg Janee <gjanee@ucop.edu>
--
-- License:
--   Copyright (c) 2012, Regents of the University of California
--   http://creativecommons.org/licenses/BSD/
--
-- ----------------------------------------------------------------------------

CREATE TABLE identifier (
  identifier TEXT NOT NULL PRIMARY KEY, -- qualified, normalized identifier
  owner TEXT NOT NULL,                  -- _o
  coOwners TEXT,                        -- _co
  createTime INTEGER NOT NULL,          -- _c
  updateTime INTEGER NOT NULL,          -- _u or _su
  status TEXT NOT NULL,                 -- _is
  mappedTitle TEXT,                     -- erc.what, datacite.title, etc.
  mappedCreator TEXT                    -- erc.who, datacite.creator, etc.
);

CREATE INDEX identifierOwnerIndex ON identifier (owner);

CREATE TABLE ownership (
  owner TEXT NOT NULL,
  identifier TEXT NOT NULL
  -- FOREIGN KEY (identifier) REFERENCES identifier,
  -- UNIQUE (owner, identifier)
);

CREATE INDEX ownershipOwnerIndex ON ownership (owner);
