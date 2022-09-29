PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE drs_object (
        id VARCHAR NOT NULL, 
        name VARCHAR, 
        self_uri VARCHAR, 
        size INTEGER, 
        created_time VARCHAR, 
        updated_time VARCHAR, 
        version VARCHAR, 
        mime_type VARCHAR, 
        checksums VARCHAR, 
        description VARCHAR, 
        aliases VARCHAR, 
        PRIMARY KEY (id)
);
INSERT INTO drs_object VALUES('NA18537.vcf.gz.tbi','NA18537.vcf.gz.tbi','drs://localhost/NA18537.vcf.gz.tbi',0,'2021-09-27T18:40:00.538843','2021-09-27T18:40:00.539022','v1','application/octet-stream','[]','','[]');
INSERT INTO drs_object VALUES('NA18537.vcf.gz','NA18537.vcf.gz','drs://localhost/NA18537.vcf.gz',0,'2021-09-27T18:40:00.538843','2021-09-27T18:40:00.539022','v1','application/octet-stream','[]','','[]');
INSERT INTO drs_object VALUES('NA18537','NA18537','drs://localhost/NA18537',0,'2021-09-27T18:40:00.538843','2021-09-27T18:40:00.539022','v1','application/octet-stream','[]','','[]');
INSERT INTO drs_object VALUES('NA20787.vcf.gz.tbi','NA20787.vcf.gz.tbi','drs://localhost/NA20787.vcf.gz.tbi',0,'2021-09-27T18:58:56.663378','2021-09-27T18:58:56.663442','v1','application/octet-stream','[]','','[]');
INSERT INTO drs_object VALUES('NA20787.vcf.gz','NA20787.vcf.gz','drs://localhost/NA20787.vcf.gz',0,'2021-09-27T18:58:56.663378','2021-09-27T18:58:56.663442','v1','application/octet-stream','[]','','[]');
INSERT INTO drs_object VALUES('NA20787','NA20787','drs://localhost/NA20787',0,'2021-09-27T18:58:56.663378','2021-09-27T18:58:56.663442','v1','application/octet-stream','[]','','[]');
CREATE TABLE access_method (
        id INTEGER NOT NULL, 
        drs_object_id INTEGER, 
        type VARCHAR, 
        access_id VARCHAR, 
        region VARCHAR, 
        url VARCHAR, 
        headers VARCHAR, 
        PRIMARY KEY (id), 
        FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
INSERT INTO access_method VALUES(1,'NA18537.vcf.gz.tbi','s3','s3.amazonaws.com/daisietestbucket1/NA18537.vcf.gz.tbi','','','[]');
INSERT INTO access_method VALUES(2,'NA18537.vcf.gz','s3','s3.amazonaws.com/daisietestbucket1/NA18537.vcf.gz','','','[]');
INSERT INTO access_method VALUES(3,'NA20787.vcf.gz.tbi','s3','s3.amazonaws.com/daisietestbucket1/NA20787.vcf.gz.tbi','','','[]');
INSERT INTO access_method VALUES(4,'NA20787.vcf.gz','s3','s3.amazonaws.com/daisietestbucket1/NA20787.vcf.gz','','','[]');
CREATE TABLE content_object (
        id INTEGER NOT NULL, 
        drs_object_id INTEGER, 
        name VARCHAR, 
        drs_uri VARCHAR, 
        contents VARCHAR, 
        PRIMARY KEY (id), 
        FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
INSERT INTO content_object VALUES(1,'NA18537','NA18537.vcf.gz','["drs://localhost/NA18537.vcf.gz"]','[]');
INSERT INTO content_object VALUES(2,'NA18537','NA18537.vcf.gz.tbi','["drs://localhost/NA18537.vcf.gz.tbi"]','[]');
INSERT INTO content_object VALUES(5,'NA20787','NA20787.vcf.gz','["drs://localhost/NA20787.vcf.gz"]','[]');
INSERT INTO content_object VALUES(6,'NA20787','NA20787.vcf.gz.tbi','["drs://localhost/NA20787.vcf.gz.tbi"]','[]');
CREATE TABLE dataset (
	id VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO dataset VALUES('controlled4');
CREATE TABLE dataset_association (
	dataset_id VARCHAR NOT NULL, 
	drs_object_id VARCHAR NOT NULL, 
	PRIMARY KEY (dataset_id, drs_object_id), 
	FOREIGN KEY(dataset_id) REFERENCES dataset (id), 
	FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
INSERT INTO dataset_association VALUES('controlled4','NA18537');
COMMIT;
