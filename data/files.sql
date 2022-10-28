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
INSERT INTO access_method VALUES(1,'NA18537.vcf.gz.tbi','s3','s3.amazonaws.com/daisietestbucket1/test/NA18537.vcf.gz.tbi','','','[]');
INSERT INTO access_method VALUES(2,'NA18537.vcf.gz','s3','s3.amazonaws.com/daisietestbucket1/test/NA18537.vcf.gz','','','[]');
INSERT INTO access_method VALUES(3,'NA20787.vcf.gz.tbi','s3','s3.amazonaws.com/daisietestbucket1/test/NA20787.vcf.gz.tbi','','','[]');
INSERT INTO access_method VALUES(4,'NA20787.vcf.gz','s3','s3.amazonaws.com/daisietestbucket1/test/NA20787.vcf.gz','','','[]');
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
CREATE TABLE contig (
	id VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO contig VALUES('1');
INSERT INTO contig VALUES('2');
INSERT INTO contig VALUES('3');
INSERT INTO contig VALUES('4');
INSERT INTO contig VALUES('5');
INSERT INTO contig VALUES('6');
INSERT INTO contig VALUES('7');
INSERT INTO contig VALUES('8');
INSERT INTO contig VALUES('9');
INSERT INTO contig VALUES('10');
INSERT INTO contig VALUES('11');
INSERT INTO contig VALUES('12');
INSERT INTO contig VALUES('13');
INSERT INTO contig VALUES('14');
INSERT INTO contig VALUES('15');
INSERT INTO contig VALUES('16');
INSERT INTO contig VALUES('17');
INSERT INTO contig VALUES('18');
INSERT INTO contig VALUES('19');
INSERT INTO contig VALUES('20');
INSERT INTO contig VALUES('21');
INSERT INTO contig VALUES('22');
INSERT INTO contig VALUES('X');
INSERT INTO contig VALUES('Y');
INSERT INTO contig VALUES('MT');
CREATE TABLE alias (
	id VARCHAR NOT NULL, 
	contig_id VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contig_id) REFERENCES contig (id)
);
INSERT INTO alias VALUES('chr1','1');
INSERT INTO alias VALUES('chr2','2');
INSERT INTO alias VALUES('chr3','3');
INSERT INTO alias VALUES('chr4','4');
INSERT INTO alias VALUES('chr5','5');
INSERT INTO alias VALUES('chr6','6');
INSERT INTO alias VALUES('chr7','7');
INSERT INTO alias VALUES('chr8','8');
INSERT INTO alias VALUES('chr9','9');
INSERT INTO alias VALUES('chr10','10');
INSERT INTO alias VALUES('chr11','11');
INSERT INTO alias VALUES('chr12','12');
INSERT INTO alias VALUES('chr13','13');
INSERT INTO alias VALUES('chr14','14');
INSERT INTO alias VALUES('chr15','15');
INSERT INTO alias VALUES('chr16','16');
INSERT INTO alias VALUES('chr17','17');
INSERT INTO alias VALUES('chr18','18');
INSERT INTO alias VALUES('chr19','19');
INSERT INTO alias VALUES('chr20','20');
INSERT INTO alias VALUES('chr21','21');
INSERT INTO alias VALUES('chrX','X');
INSERT INTO alias VALUES('chrY','Y');
INSERT INTO alias VALUES('chrMT','MT');
INSERT INTO alias VALUES('Chr1','1');
INSERT INTO alias VALUES('Chr2','2');
INSERT INTO alias VALUES('Chr3','3');
INSERT INTO alias VALUES('Chr4','4');
INSERT INTO alias VALUES('Chr5','5');
INSERT INTO alias VALUES('Chr6','6');
INSERT INTO alias VALUES('Chr7','7');
INSERT INTO alias VALUES('Chr8','8');
INSERT INTO alias VALUES('Chr9','9');
INSERT INTO alias VALUES('Chr10','10');
INSERT INTO alias VALUES('Chr11','11');
INSERT INTO alias VALUES('Chr12','12');
INSERT INTO alias VALUES('Chr13','13');
INSERT INTO alias VALUES('Chr14','14');
INSERT INTO alias VALUES('Chr15','15');
INSERT INTO alias VALUES('Chr16','16');
INSERT INTO alias VALUES('Chr17','17');
INSERT INTO alias VALUES('Chr18','18');
INSERT INTO alias VALUES('Chr19','19');
INSERT INTO alias VALUES('Chr20','20');
INSERT INTO alias VALUES('Chr21','21');
INSERT INTO alias VALUES('ChrX','X');
INSERT INTO alias VALUES('ChrY','Y');
INSERT INTO alias VALUES('ChrMT','MT');
INSERT INTO alias VALUES('x','X');
INSERT INTO alias VALUES('y','Y');
INSERT INTO alias VALUES('mt','MT');
CREATE TABLE variantfile (
	id VARCHAR NOT NULL, 
	genomic_id VARCHAR,
	drs_object_id VARCHAR, 
	indexed INTEGER,
	chr_prefix VARCHAR,
	reference_genome VARCHAR,
	PRIMARY KEY (id), 
	FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
CREATE TABLE pos_bucket (
	id INTEGER PRIMARY KEY AUTOINCREMENT, 
	pos_bucket_id INTEGER NOT NULL, 
	contig_id VARCHAR, 
	FOREIGN KEY(contig_id) REFERENCES contig (id)
);
CREATE TABLE header (
	id INTEGER PRIMARY KEY AUTOINCREMENT, 
	text VARCHAR NOT NULL
);
CREATE TABLE contig_variantfile_association (
	contig_id VARCHAR NOT NULL, 
	variantfile_id VARCHAR NOT NULL, 
	PRIMARY KEY (contig_id, variantfile_id), 
	FOREIGN KEY(contig_id) REFERENCES contig (id), 
	FOREIGN KEY(variantfile_id) REFERENCES variantfile (id)
);
CREATE TABLE header_variantfile_association (
	header_id INTEGER NOT NULL, 
	variantfile_id VARCHAR NOT NULL, 
	PRIMARY KEY (header_id, variantfile_id), 
	FOREIGN KEY(header_id) REFERENCES header (id), 
	FOREIGN KEY(variantfile_id) REFERENCES variantfile (id)
);
CREATE TABLE pos_bucket_variantfile_association (
	pos_bucket_id INTEGER NOT NULL, 
	variantfile_id VARCHAR NOT NULL, 
	bucket_count INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY (pos_bucket_id, variantfile_id), 
	FOREIGN KEY(pos_bucket_id) REFERENCES pos_bucket (id), 
	FOREIGN KEY(variantfile_id) REFERENCES variantfile (id)
);
CREATE TABLE sample (
	id INTEGER PRIMARY KEY AUTOINCREMENT, 
	sample_id VARCHAR, 
	variantfile_id VARCHAR, 
	FOREIGN KEY(variantfile_id) REFERENCES variantfile (id)
);
COMMIT;