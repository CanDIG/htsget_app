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
CREATE TABLE access_method (
        id SERIAL PRIMARY KEY,
        drs_object_id VARCHAR,
        type VARCHAR,
        access_id VARCHAR,
        region VARCHAR,
        url VARCHAR,
        headers VARCHAR,
        FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
CREATE TABLE content_object (
        id SERIAL PRIMARY KEY,
        drs_object_id VARCHAR,
        name VARCHAR,
        contents_id VARCHAR,
        drs_uri VARCHAR,
        contents VARCHAR,
        FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
CREATE TABLE cohort (
	id VARCHAR NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
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
INSERT INTO alias VALUES('chr22','22');
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
INSERT INTO alias VALUES('Chr22','22');
INSERT INTO alias VALUES('ChrX','X');
INSERT INTO alias VALUES('ChrY','Y');
INSERT INTO alias VALUES('ChrMT','MT');
INSERT INTO alias VALUES('x','X');
INSERT INTO alias VALUES('y','Y');
INSERT INTO alias VALUES('mt','MT');
INSERT INTO alias VALUES('M','MT');
INSERT INTO alias VALUES('chrM','MT');
INSERT INTO alias VALUES('ChrM','MT');
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
	id SERIAL PRIMARY KEY,
	pos_bucket_id INTEGER NOT NULL,
	contig_id VARCHAR,
	FOREIGN KEY(contig_id) REFERENCES contig (id)
);
CREATE TABLE header (
	id SERIAL PRIMARY KEY,
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
	id SERIAL PRIMARY KEY,
	sample_id VARCHAR,
	variantfile_id VARCHAR,
	FOREIGN KEY(variantfile_id) REFERENCES variantfile (id)
);

-- ncbiRefSeq table modified from https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/

-- field	example	description
-- reference_genome	hg38	Reference genome build
-- gene_name	DDX11L1	varchar(255)	values	Gene name from http://www.genenames.org/
-- transcript_name	NR_046018.2	Transcript name from NCBI RefSeq
-- contig	1	Reference sequence chromosome or scaffold
-- start	11873	Transcription start position (or end position for minus strand item)
-- endpos	14409	Transcription end position (or start position for minus strand item)

CREATE TABLE ncbiRefSeq (
	id SERIAL PRIMARY KEY,
	reference_genome varchar(10) NOT NULL,
	gene_name varchar(255) NOT NULL,
	transcript_name varchar(255) NOT NULL,
	contig varchar(25) NOT NULL,
	start int NOT NULL,
	endpos int NOT NULL,
	UNIQUE(reference_genome, contig, gene_name, transcript_name)
);

-- insert reference sequences for chromosomes: ncbi reference name is in transcript name, but gene name is empty
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000001.11', '1', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000002.12', '2', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000003.12', '3', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000004.12', '4', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000005.10', '5', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000006.12', '6', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000007.14', '7', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000008.11', '8', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000009.12', '9', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000010.11', '10', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000011.10', '11', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000012.12', '12', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000013.11', '13', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000014.9', '14', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000015.10', '15', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000016.10', '16', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000017.11', '17', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000018.10', '18', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000019.10', '19', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000020.11', '20', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000021.9', '21', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000022.11', '22', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000023.11', 'X', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_000024.10', 'Y', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg38', 'NC_012920.1', 'MT', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000001.10', '1', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000002.11', '2', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000003.11', '3', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000004.11', '4', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000005.9', '5', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000006.11', '6', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000007.13', '7', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000008.10', '8', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000009.11', '9', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000010.10', '10', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000011.9', '11', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000012.11', '12', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000013.10', '13', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000014.8', '14', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000015.9', '15', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000016.9', '16', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000017.10', '17', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000018.9', '18', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000019.9', '19', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000020.10', '20', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000021.8', '21', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000022.10', '22', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000023.10', 'X', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_000024.9', 'Y', 0, 0, '') ON CONFLICT DO NOTHING;
INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES ('hg37', 'NC_012920.1', 'MT', 0, 0, '') ON CONFLICT DO NOTHING;

COMMIT;
