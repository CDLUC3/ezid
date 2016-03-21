-- We assume that the database's default collation is case-insensitive
-- (e.g., utf8_general_ci).  This is desirable for ordering purposes,
-- and it will also force usernames and such to be case-insensitively
-- unique.  But identifiers are case-sensitive.  Additionally, the
-- restricted character set of identifiers allows us to use ASCII
-- instead of UTF-8.

ALTER TABLE ezidapp_crossrefqueue MODIFY identifier VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_crossrefqueue MODIFY owner VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_datacitequeue MODIFY identifier VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_downloadqueue MODIFY requestor VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_downloadqueue MODIFY coOwners LONGTEXT NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_downloadqueue MODIFY currentOwner VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_downloadqueue MODIFY lastId VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_shoulder MODIFY prefix VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';

-- A gotcha: MySQL's UTF-8 character set is capable of storing the
-- Basic Multilingual Plane only (surprise!), so for those fields that
-- hold externally-supplied, uncontrolled Unicode input, the character
-- set and collation must be changed.

ALTER TABLE ezidapp_crossrefqueue MODIFY message LONGTEXT NOT NULL
  COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_datacitequeue MODIFY error LONGTEXT NOT NULL
  COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_downloadqueue MODIFY rawRequest LONGTEXT NOT NULL
  COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_downloadqueue MODIFY columns LONGTEXT NOT NULL
  COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_downloadqueue MODIFY notify LONGTEXT NOT NULL
  COLLATE 'utf8mb4_general_ci';
