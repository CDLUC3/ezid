mysql -h127.0.0.1 -u root << EOF
            drop database if exists ezid_test_db;
            create database ezid_test_db;
            use ezid_test_db;
            drop user if exists 'ezid_test_user'@'%';
            create user 'ezid_test_user'@'%' identified by 'ezid_test_pw';
            grant all privileges on ezid_test_db.* to 'ezid_test_user'@'%';
            flush privileges;
