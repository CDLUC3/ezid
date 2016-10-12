-- We assume that the database's default collation is case-insensitive
-- (e.g., utf8_general_ci).  This is desirable for ordering purposes,
-- and it will also force usernames and such to be case-insensitively
-- unique.  But identifiers are case-sensitive.  Additionally, the
-- restricted character set of identifiers allows us to use ASCII
-- instead of UTF-8, which decreases index size.

ALTER TABLE ezidapp_searchgroup MODIFY pid VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_searchuser MODIFY pid VARCHAR(255) NOT NULL
  COLLATE 'ascii_bin';
ALTER TABLE ezidapp_searchidentifier MODIFY identifier VARCHAR(255)
  NOT NULL COLLATE 'ascii_bin';
ALTER TABLE ezidapp_linkchecker MODIFY identifier VARCHAR(255)
  NOT NULL COLLATE 'ascii_bin';

-- A gotcha: MySQL's UTF-8 character set is capable of storing the
-- Basic Multilingual Plane only (surprise!), so for those fields that
-- hold externally-supplied, uncontrolled Unicode input, the character
-- set and collation must be changed.

ALTER TABLE ezidapp_searchidentifier MODIFY unavailableReason LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY crossrefMessage LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourceCreator LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourceTitle LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourcePublisher LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourcePublicationDate LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourceType LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY keywords LONGTEXT
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourceCreatorPrefix VARCHAR(50)
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourceTitlePrefix VARCHAR(50)
  NOT NULL COLLATE 'utf8mb4_general_ci';
ALTER TABLE ezidapp_searchidentifier MODIFY resourcePublisherPrefix VARCHAR(50)
  NOT NULL COLLATE 'utf8mb4_general_ci';

-- Fixups.  A couple columns are not required within Django, but
-- because EZID always supplies defaults, they can be declared NOT
-- NULL in the database.  Note the unfortunate necessity of referring
-- to Django-generated index names.

ALTER TABLE ezidapp_searchidentifier DROP FOREIGN KEY
  ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id;
ALTER TABLE ezidapp_searchidentifier MODIFY ownergroup_id INT NOT NULL;
ALTER TABLE ezidapp_searchidentifier ADD CONSTRAINT
  ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id
  FOREIGN KEY (ownergroup_id) REFERENCES ezidapp_searchgroup (id);

ALTER TABLE ezidapp_searchidentifier DROP FOREIGN KEY
  ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id;
ALTER TABLE ezidapp_searchidentifier MODIFY profile_id INT NOT NULL;
ALTER TABLE ezidapp_searchidentifier ADD CONSTRAINT
  ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id
  FOREIGN KEY (profile_id) REFERENCES ezidapp_searchprofile (id);

-- Create the FULLTEXT indexes...

CREATE FULLTEXT INDEX ezidapp_searchidentifier_resourceTitle
  ON ezidapp_searchidentifier (resourceTitle);
CREATE FULLTEXT INDEX ezidapp_searchidentifier_resourceCreator
  ON ezidapp_searchidentifier (resourceCreator);
CREATE FULLTEXT INDEX ezidapp_searchidentifier_resourcePublisher
  ON ezidapp_searchidentifier (resourcePublisher);
CREATE FULLTEXT INDEX ezidapp_searchidentifier_keywords
  ON ezidapp_searchidentifier (keywords);

-- The following greatly improves index statistics.

ALTER TABLE ezidapp_searchidentifier STATS_SAMPLE_PAGES = 2000;
