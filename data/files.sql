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
CREATE TABLE contig (
        id VARCHAR NOT NULL, 
        PRIMARY KEY (id)
);
INSERT INTO contig VALUES('chr1');
INSERT INTO contig VALUES('chr2');
INSERT INTO contig VALUES('chr3');
INSERT INTO contig VALUES('chr4');
INSERT INTO contig VALUES('chr5');
INSERT INTO contig VALUES('chr6');
INSERT INTO contig VALUES('chr7');
INSERT INTO contig VALUES('chr8');
INSERT INTO contig VALUES('chr9');
INSERT INTO contig VALUES('chr10');
INSERT INTO contig VALUES('chr11');
INSERT INTO contig VALUES('chr12');
INSERT INTO contig VALUES('chr13');
INSERT INTO contig VALUES('chr14');
INSERT INTO contig VALUES('chr15');
INSERT INTO contig VALUES('chr16');
INSERT INTO contig VALUES('chr17');
INSERT INTO contig VALUES('chr18');
INSERT INTO contig VALUES('chr19');
INSERT INTO contig VALUES('chr20');
INSERT INTO contig VALUES('chr21');
INSERT INTO contig VALUES('chr22');
INSERT INTO contig VALUES('chrX');
INSERT INTO contig VALUES('chrY');
CREATE TABLE alias (
	id VARCHAR NOT NULL, 
	contig_id VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contig_id) REFERENCES contig (id)
);
INSERT INTO alias VALUES('1','chr1');
INSERT INTO alias VALUES('2','chr2');
INSERT INTO alias VALUES('3','chr3');
INSERT INTO alias VALUES('4','chr4');
INSERT INTO alias VALUES('5','chr5');
INSERT INTO alias VALUES('6','chr6');
INSERT INTO alias VALUES('7','chr7');
INSERT INTO alias VALUES('8','chr8');
INSERT INTO alias VALUES('9','chr9');
INSERT INTO alias VALUES('10','chr10');
INSERT INTO alias VALUES('11','chr11');
INSERT INTO alias VALUES('12','chr12');
INSERT INTO alias VALUES('13','chr13');
INSERT INTO alias VALUES('14','chr14');
INSERT INTO alias VALUES('15','chr15');
INSERT INTO alias VALUES('16','chr16');
INSERT INTO alias VALUES('17','chr17');
INSERT INTO alias VALUES('18','chr18');
INSERT INTO alias VALUES('19','chr19');
INSERT INTO alias VALUES('20','chr20');
INSERT INTO alias VALUES('21','chr21');
INSERT INTO alias VALUES('X','chrX');
INSERT INTO alias VALUES('Y','chrY');
INSERT INTO alias VALUES('Chr1','chr1');
INSERT INTO alias VALUES('Chr2','chr2');
INSERT INTO alias VALUES('Chr3','chr3');
INSERT INTO alias VALUES('Chr4','chr4');
INSERT INTO alias VALUES('Chr5','chr5');
INSERT INTO alias VALUES('Chr6','chr6');
INSERT INTO alias VALUES('Chr7','chr7');
INSERT INTO alias VALUES('Chr8','chr8');
INSERT INTO alias VALUES('Chr9','chr9');
INSERT INTO alias VALUES('Chr10','chr10');
INSERT INTO alias VALUES('Chr11','chr11');
INSERT INTO alias VALUES('Chr12','chr12');
INSERT INTO alias VALUES('Chr13','chr13');
INSERT INTO alias VALUES('Chr14','chr14');
INSERT INTO alias VALUES('Chr15','chr15');
INSERT INTO alias VALUES('Chr16','chr16');
INSERT INTO alias VALUES('Chr17','chr17');
INSERT INTO alias VALUES('Chr18','chr18');
INSERT INTO alias VALUES('Chr19','chr19');
INSERT INTO alias VALUES('Chr20','chr20');
INSERT INTO alias VALUES('Chr21','chr21');
INSERT INTO alias VALUES('ChrX','chrX');
INSERT INTO alias VALUES('ChrY','chrY');
INSERT INTO alias VALUES('x','chrX');
INSERT INTO alias VALUES('y','chrY');
CREATE TABLE variantfile (
	id VARCHAR NOT NULL, 
	drs_object_id VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
CREATE TABLE position (
	id INTEGER NOT NULL, 
	contig_id VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contig_id) REFERENCES contig (id)
);
CREATE TABLE header (
	id INTEGER NOT NULL, 
	text VARCHAR NOT NULL, 
	PRIMARY KEY (id, text)
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
CREATE TABLE sample (
	id VARCHAR NOT NULL, 
	variantfile_id VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(variantfile_id) REFERENCES variantfile (id)
);
COMMIT;