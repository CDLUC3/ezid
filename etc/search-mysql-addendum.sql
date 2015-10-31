-- We assume that the database's default collation is case-insensitive
-- (e.g., utf8_general_ci).  This is desirable for ordering purposes,
-- and it will also force usernames and such to be case-insensitively
-- unique.  But identifiers are case-sensitive.  (For some bizarre
-- reason the "NOT NULL" has to be re-asserted.)

ALTER TABLE ezidapp_searchgroup MODIFY pid VARCHAR(255) NOT NULL
  COLLATE 'utf8_bin';
ALTER TABLE ezidapp_searchuser MODIFY pid VARCHAR(255) NOT NULL
  COLLATE 'utf8_bin';
ALTER TABLE ezidapp_searchidentifier MODIFY identifier VARCHAR(255)
  NOT NULL COLLATE 'utf8_bin';

-- Create the FULLTEXT indexes...

CREATE FULLTEXT INDEX ezidapp_searchidentifier_resourceTitle
  ON ezidapp_searchidentifier (resourceTitle);
CREATE FULLTEXT INDEX ezidapp_searchidentifier_resourceCreator
  ON ezidapp_searchidentifier (resourceCreator);
CREATE FULLTEXT INDEX ezidapp_searchidentifier_resourcePublisher
  ON ezidapp_searchidentifier (resourcePublisher);
CREATE FULLTEXT INDEX ezidapp_searchidentifier_keywords
  ON ezidapp_searchidentifier (keywords);
