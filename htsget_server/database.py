from sqlalchemy.orm import declarative_base, relationship, sessionmaker, aliased
from sqlalchemy import Column, Integer, String, Boolean, MetaData, ForeignKey, Table, create_engine, select
import json
import re
from datetime import datetime
from random import randint
from time import sleep
from config import DB_PATH, BUCKET_SIZE, HTSGET_URL
from flask import Flask
import logging

app = Flask(__name__)

engine = create_engine(DB_PATH, echo=False)

ObjectDBBase = declarative_base()


## Variant search entities

## relationships
# each contig is in many variantfiles and each variantfile contains many contigs
contig_variantfile_association = Table(
    'contig_variantfile_association', ObjectDBBase.metadata,
    Column('contig_id', ForeignKey('contig.id'), primary_key=True),
    Column('variantfile_id', ForeignKey('variantfile.id'), primary_key=True)
)


class PositionBucketVariantFileAssociation(ObjectDBBase):
    __tablename__ = 'pos_bucket_variantfile_association'
    pos_bucket_id = Column(Integer, ForeignKey('pos_bucket.id'), primary_key=True)
    variantfile_id = Column(String, ForeignKey('variantfile.id'), primary_key=True)
    bucket_count = Column(Integer, default=0)
    def __repr__(self):
        result = {
            'pos_bucket_id': self.pos_bucket_id,
            'variantfile_id': self.variantfile_id,
            'count': self.bucket_count
        }

        return json.dumps(result)

# each pos_bucket is in many variantfiles and each variantfile contains many pos_buckets
pos_bucket_variantfile_association = Table(
    'pos_bucket_variantfile_association', ObjectDBBase.metadata,
    Column('pos_bucket_id', ForeignKey('pos_bucket.id'), primary_key=True),
    Column('variantfile_id', ForeignKey('variantfile.id'), primary_key=True),
    Column('bucket_count', default=0), extend_existing=True
)


# each header is in many variantfiles and each variantfile contains many headers
header_variantfile_association = Table(
    'header_variantfile_association', ObjectDBBase.metadata,
    Column('header_id', ForeignKey('header.id'), primary_key=True),
    Column('variantfile_id', ForeignKey('variantfile.id'), primary_key=True)
)


class Alias(ObjectDBBase):
    __tablename__ = 'alias'
    id = Column(String, primary_key=True)

    # an alias maps to one contig
    contig_id = Column(String, ForeignKey('contig.id'))
    contig = relationship(
        "Contig",
        back_populates="aliases",
        uselist=False
    )


class Contig(ObjectDBBase):
    __tablename__ = 'contig'
    id = Column(String, primary_key=True)

    # a contig can have many aliases
    aliases = relationship(
        "Alias",
        back_populates="contig"
    )

    # a contig can be part of many variantfiles
    associated_variantfiles = relationship("VariantFile",
        secondary=contig_variantfile_association,
        back_populates="associated_contigs"
    )

    # a contig can have many positions
    pos_buckets = relationship(
        "PositionBucket",
        back_populates="contig"
    )


class VariantFile(ObjectDBBase):
    __tablename__ = 'variantfile'
    id = Column(String, primary_key=True)
    indexed = Column(Integer)
    chr_prefix = Column(String)
    reference_genome = Column(String)

    # a variantfile maps to a drs object
    drs_object_id = Column(String, ForeignKey('drs_object.id'))
    drs_object = relationship(
        "DrsObject",
        back_populates="variantfile",
        uselist=False
    )

    # a variantfile can contain many contigs
    associated_contigs = relationship("Contig",
        secondary=contig_variantfile_association,
        back_populates="associated_variantfiles"
    )

    # a variantfile can contain many pos_buckets
    associated_pos_buckets = relationship("PositionBucket",
        secondary=pos_bucket_variantfile_association,
        back_populates="associated_variantfiles"
    )

    # a variantfile can contain many headers
    associated_headers = relationship("Header",
        secondary=header_variantfile_association,
        back_populates="associated_variantfiles"
    )

    # a variantfile can contain several samples
    samples = relationship(
        "Sample",
        back_populates="variantfile",
        cascade="all, delete, delete-orphan"
    )
    def __repr__(self):
        result = {
            'id': self.id,
            'drsobject': self.drs_object_id,
            'indexed': self.indexed,
            'chr_prefix': self.chr_prefix,
            'reference_genome': self.reference_genome,
            'samples': []
        }
        for sample in self.samples:
            result['samples'].append(sample.sample_id)

        return json.dumps(result)



class PositionBucket(ObjectDBBase):
    __tablename__ = 'pos_bucket'
    id = Column(Integer, primary_key=True)
    pos_bucket_id = Column(Integer) # each bucket contains 10 bp of positions

    # a pos_bucket is part of a single contig
    contig_id = Column(String, ForeignKey('contig.id'))
    contig = relationship(
        "Contig",
        back_populates="pos_buckets",
        uselist=False
    )
    # a pos_bucket occurs in many variantfiles
    associated_variantfiles = relationship("VariantFile",
        secondary=pos_bucket_variantfile_association,
        back_populates="associated_pos_buckets"
    )
    def __repr__(self):
        result = {
            'id': self.id,
            'contig_id': self.contig_id,
            'variantfiles': []
        }
        for varfile_assoc in self.associated_variantfiles:
            result['variantfiles'].append(varfile_assoc.id)

        return json.dumps(result)


class Sample(ObjectDBBase):
    __tablename__ = 'sample'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sample_id = Column(String)

    # a sample is in a single variantfile
    variantfile_id = Column(String, ForeignKey('variantfile.id'))
    variantfile = relationship(
        "VariantFile",
        back_populates="samples",
        uselist=False
    )
    def __repr__(self):
        result = {
            'id': self.sample_id,
            'variantfile_id': self.variantfile_id
        }
        return json.dumps(result)


class Header(ObjectDBBase):
    __tablename__ = 'header'
    id = Column(Integer, primary_key=True)
    text = Column(String)

    # a header is in many variantfiles
    associated_variantfiles = relationship("VariantFile",
        secondary=header_variantfile_association,
        back_populates="associated_headers"
    )
    def __repr__(self):
        result = {
            'id': self.id,
            'text': self.text,
            'variantfiles': []
        }
        for varfile_assoc in self.associated_variantfiles:
            result['variantfiles'].append(varfile_assoc.id)
        return json.dumps(result)


## gene search entities

class NCBIRefSeq(ObjectDBBase):
    __tablename__ = 'ncbirefseq'
    id = Column(Integer, primary_key=True)
    reference_genome = Column(String)
    gene_name = Column(String)
    transcript_name = Column(String)
    contig = Column(String)
    start = Column(Integer)
    endpos = Column(Integer)

    def __repr__(self):
        result = {
            'id': self.id,
            'reference_genome': self.reference_genome,
            'gene_name': self.gene_name,
            'transcript_name': self.transcript_name,
            'contig': self.contig,
            'start': self.start,
            'end': self.endpos
        }
        return json.dumps(result)


## CanDIG cohorts entities
class Cohort(ObjectDBBase):
    __tablename__ = 'cohort'
    id = Column(String, primary_key=True)
    associated_drs = relationship("DrsObject", back_populates="cohort", cascade="all, delete, delete-orphan")
    def __repr__(self):
        result = {
            'id': self.id,
            'drsobjects': []
        }
        for drs_assoc in self.associated_drs:
            result['drsobjects'].append(drs_assoc.self_uri)

        return json.dumps(result)


## DRS database entities
class DrsObject(ObjectDBBase):
    __tablename__ = 'drs_object'
    id = Column(String, primary_key=True)
    name = Column(String)
    self_uri = Column(String)
    size = Column(Integer, default=0)
    created_time = Column(String, default=datetime.today().isoformat())
    updated_time = Column(String, default=datetime.today().isoformat())
    version = Column(String, default='')
    mime_type = Column(String, default='application/octet-stream')
    checksums = Column(String, default='[]') # JSON array of strings
    access_methods = relationship("AccessMethod", back_populates="drs_object", cascade="all, delete, delete-orphan")
    description = Column(String, default='')
    aliases = Column(String, default='[]') # JSON array of strings of aliases
    contents = relationship("ContentsObject", cascade="all, delete, delete-orphan")
    cohort_id = Column(String, ForeignKey('cohort.id'))
    cohort = relationship("Cohort", back_populates="associated_drs")
    variantfile = relationship("VariantFile", back_populates="drs_object", cascade="all, delete")

    def __repr__(self):
        result = {
            'id': self.id,
            'name': self.name,
            'self_uri': self.self_uri,
            'size': self.size,
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'version': self.version,
            'checksums': json.loads(self.checksums),
            'description': self.description,
            'mime_type': self.mime_type,
            'aliases': json.loads(self.aliases)
        }
        if len(list(self.contents)) > 0:
            result['contents'] = json.loads(self.contents.__repr__())
        if len(list(self.access_methods)) > 0:
            result['access_methods'] = json.loads(self.access_methods.__repr__())
        if self.cohort is not None:
            result['cohort'] = self.cohort_id
        if self.variantfile is not None and len(self.variantfile) > 0:
            result['indexed'] = self.variantfile[0].indexed
            result['reference_genome'] = self.variantfile[0].reference_genome
        return json.dumps(result)


class AccessMethod(ObjectDBBase):
    __tablename__ = 'access_method'
    id = Column(Integer, primary_key=True)
    drs_object_id = Column(Integer, ForeignKey('drs_object.id'))
    drs_object = relationship("DrsObject", back_populates="access_methods")
    type = Column(String, default='')
    access_id = Column(String, default='')
    region = Column(String, default='')
    url = Column(String, default='')
    headers = Column(String, default='[]') # JSON array of strings

    def __repr__(self):
        result = {
            'type': self.type
        }
        if self.region != "":
            result['region'] = self.region
        if self.url != "":
            result['access_url'] = {
                'url': self.url,
                'headers': json.loads(self.headers)
            }
        if self.access_id != "":
            result['access_id'] = self.access_id

        return json.dumps(result)


class ContentsObject(ObjectDBBase):
    __tablename__ = 'content_object'
    id = Column(Integer, primary_key=True)
    drs_object_id = Column(Integer, ForeignKey('drs_object.id'))
    drs_object = relationship("DrsObject", back_populates="contents")
    name = Column(String, default='') # like a filename
    contents_id = Column(String)
    drs_uri = Column(String, default='[]') # JSON array of strings of DRS id URIs
    contents = Column(String, default='[]') # JSON array of ContentsObject.ids
    def __repr__(self):
        result = {
            'name': self.name,
            'id': self.contents_id,
            'drs_uri': json.loads(self.drs_uri)
        }
        if len(json.loads(self.contents)) > 0:
            result['contents'] = json.loads(self.contents)

        return json.dumps(result)


ObjectDBBase.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


""" Helper Functions"""
def get_drs_object(object_id, expand=False, tries=1):
    if tries > 3:
        raise Exception(f"Exception in get_drs_object {object_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    with Session() as session:
        try:
            result = session.query(DrsObject).filter_by(id=object_id).one_or_none()
            if result is not None:
                new_obj = json.loads(str(result))
    #         if expand:
    #             expand doesn't do anything on this DRS server
                return new_obj
        except Exception as e:
            app.logger.info(f"Exception in get_drs_object {object_id}: {str(e)}, trying again")
            return get_drs_object(object_id, expand, tries=tries+1)
        return None


def list_drs_objects(cohort_id=None):
    with Session() as session:
        if cohort_id is not None:
            result = session.query(DrsObject).filter_by(cohort_id=cohort_id).all()
        else:
            result = session.query(DrsObject).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_drs_object(obj):
    with Session() as session:
        new_object = session.query(DrsObject).filter_by(id=obj['id']).one_or_none()
        if new_object is None:
            new_object = DrsObject()

        # required fields:
        new_object.id = obj['id']
        if 'name' in obj:
            new_object.name = obj['name']
        else:
            new_object.name = obj['id']

        # optional string fields
        new_object.self_uri = f'{HTSGET_URL.replace("http://", "drs://").replace("https://", "drs://")}/{new_object.name}'
        if 'created_time' in obj:
            new_object.created_time = obj['created_time']
        if 'updated_time' in obj:
            new_object.updated_time = obj['updated_time']
        if 'mime_type' in obj:
            new_object.mime_type = obj['mime_type']
        if 'version' in obj:
            new_object.version = obj['version']
        if 'size' in obj:
            new_object.size = obj['size']
        if 'description' in obj:
            new_object.description = obj['description']
        if 'cohort' in obj:
            cohort = session.query(Cohort).filter_by(id=obj['cohort']).one_or_none()
            if cohort is None:
                create_cohort({"id": obj["cohort"], "drsobjects": []})
            new_object.cohort_id = obj['cohort']

        # json arrays stored as strings
        if 'checksums' in obj:
            new_object.checksums = json.dumps(obj['checksums'])
        if 'aliases' in obj:
            new_object.aliases = json.dumps(obj['aliases'])

        # access methods is special
        if 'access_methods' not in obj:
            obj['access_methods'] = []
        # only add access methods after removing any previous ones
        if len(new_object.access_methods) != 0:
            for method in new_object.access_methods:
                session.delete(method)
                session.commit()
        for method in obj['access_methods']:
            new_method = AccessMethod()
            new_method.drs_object_id = new_object.id
            new_method.type = method['type']
            if 'region' in method:
                new_method.region = method['region']
            if 'access_id' in method:
                new_method.access_id = method['access_id']
            if 'access_url' in method:
                new_method.url = method['access_url']['url']
                if 'headers' in method['access_url']:
                    new_method.headers = json.dumps(method['access_url']['headers'])
            session.add(new_method)

        # contents objects are special
        if 'contents' not in obj:
            obj['contents'] = []
        if len(new_object.contents) != 0:
            for contents in new_object.contents:
                session.delete(contents)
                session.commit()
        for contents in obj['contents']:
            new_contents = ContentsObject()
            new_contents.drs_object_id = new_object.id
            new_contents.name = contents['name']
            if 'drs_uri' in contents:
                new_contents.drs_uri = json.dumps(contents['drs_uri'])
            if 'contents' in contents:
                new_contents.contents = json.dumps(contents['contents'])
            if 'id' in contents:
                new_contents.contents_id = contents['id']
            session.add(new_contents)
        session.add(new_object)
        session.commit()

    # if we have reference_genome info, it's a GenomicDrsObject and needs a variantfile:
    if 'reference_genome' in obj:
        create_variantfile({"id": obj["id"], "reference_genome": obj["reference_genome"]})

    result = session.query(DrsObject).filter_by(id=obj['id']).one_or_none()
    return json.loads(str(result))


def delete_drs_object(obj_id):
    with Session() as session:
        new_object = session.query(DrsObject).filter_by(id=obj_id).one()
        cohort = session.query(Cohort).filter_by(id=new_object.cohort_id).one_or_none()
        if new_object.description in ["wgs", "wts"]:
            # this is a GenomicDrsObject; we need to delete any indexed variantfiles
            variantfiles = session.query(VariantFile).filter_by(drs_object_id=new_object.id).all()
            for vf in variantfiles:
                session.delete(vf)
                session.commit()
        session.delete(new_object)
        session.commit()
        return json.loads(str(new_object))


def get_cohort(cohort_id):
    with Session() as session:
        result = session.query(Cohort).filter_by(id=cohort_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def list_cohorts():
    with Session() as session:
        result = session.query(Cohort).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_cohort(obj):
    with Session() as session:
        new_cohort = session.query(Cohort).filter_by(id=obj['id']).one_or_none()
        if new_cohort is None:
            new_cohort = Cohort()
        new_cohort.id = obj['id']
        for drs_uri in obj['drsobjects']:
            new_drs = session.query(DrsObject).filter_by(self_uri=drs_uri).one_or_none()
            if new_drs is not None:
                new_cohort.associated_drs.append(new_drs)
        session.add(new_cohort)
        session.commit()
        result = session.query(Cohort).filter_by(id=obj['id']).one_or_none()
        if result is not None:
            return json.loads(str(result))
        return None


def delete_cohort(cohort_id):
    with Session() as session:
        cohort_objs = session.query(Cohort).filter_by(id=cohort_id).all()
        for cohort_obj in cohort_objs:
            for drs_obj in cohort_obj.associated_drs:
                session.delete(drs_obj)
                session.commit()
            session.delete(cohort_obj)
            session.commit()
        session.commit()
        return json.loads(str(cohort_objs))


def list_refseqs(reference_genome="hg38"):
    with Session() as session:
        result = session.query(NCBIRefSeq).filter(NCBIRefSeq.reference_genome==reference_genome, NCBIRefSeq.gene_name!="").all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def search_refseqs(query, type):
    with Session() as session:
        if type == "transcript_name":
            result = session.query(NCBIRefSeq).filter(NCBIRefSeq.transcript_name.like(f'{query}%')).order_by(NCBIRefSeq.transcript_name).order_by(NCBIRefSeq.reference_genome).all()
        else:
            result = session.query(NCBIRefSeq).filter(NCBIRefSeq.gene_name.like(f'{query}%')).order_by(NCBIRefSeq.gene_name).order_by(NCBIRefSeq.reference_genome).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def get_refseq_for_chromosome(reference_genome="hg38", contig=None):
    with Session() as session:
        result = session.query(NCBIRefSeq).filter(NCBIRefSeq.reference_genome==reference_genome, NCBIRefSeq.contig==contig).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))['transcript_name']
            return new_obj
        return None


def get_chromosome_for_refseq(refseq=None):
    with Session() as session:
        result = session.query(NCBIRefSeq).filter(NCBIRefSeq.transcript_name==refseq, NCBIRefSeq.start==0).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))['contig']
            return new_obj
        return None


def get_variantfile(variantfile_id, tries=1):
    if tries > 3:
        raise Exception(f"Exception in get_variantfile {variantfile_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    with Session() as session:
        try:
            result = session.query(VariantFile).filter_by(id=variantfile_id).one_or_none()
            if result is not None:
                new_obj = json.loads(str(result))
                return new_obj
        except Exception as e:
            app.logger.info(f"Exception in get_variantfile {variantfile_id}: {str(e)}, trying again")
            return get_variantfile(variantfile_id, tries=tries+1)
        return None


def create_variantfile(obj):
    # obj = {"id", "reference_genome"}
    with Session() as session:
        new_variantfile = session.query(VariantFile).filter_by(id=obj['id']).one_or_none()
        if new_variantfile is None:
            new_variantfile = VariantFile()
            new_variantfile.indexed = 0
            new_variantfile.chr_prefix = ''
        new_variantfile.id = obj['id']
        new_variantfile.reference_genome = obj['reference_genome']
        new_drs = session.query(DrsObject).filter_by(id=obj['id']).one_or_none()
        if new_drs is not None:
            new_variantfile.drs_object_id = new_drs.id
        else:
            raise Exception(f"Cannot create variantfile {obj['id']}: no corresponding DRS object")
        session.add(new_variantfile)
        session.commit()
        result = session.query(VariantFile).filter_by(id=obj['id']).one_or_none()
        if result is not None:
            return json.loads(str(result))
    return None


def mark_variantfile_as_indexed(variantfile_id):
    with Session() as session:
        new_variantfile = session.query(VariantFile).filter_by(id=variantfile_id).one_or_none()
        if new_variantfile is not None:
            new_variantfile.indexed = 1
            session.add(new_variantfile)
            session.commit()


def mark_variantfile_as_not_indexed(variantfile_id):
    with Session() as session:
        new_variantfile = session.query(VariantFile).filter_by(id=variantfile_id).one_or_none()
        if new_variantfile is not None:
            new_variantfile.indexed = 0
            session.add(new_variantfile)
            session.commit()


def set_variantfile_prefix(obj):
    # obj = {'variantfile_id', 'chr_prefix'}
    with Session() as session:
        new_variantfile = session.query(VariantFile).filter_by(id=obj['variantfile_id']).one_or_none()
        if new_variantfile is None:
            return None
        new_variantfile.chr_prefix = obj['chr_prefix']
        session.add(new_variantfile)
        session.commit()
        result = session.query(VariantFile).filter_by(id=obj['variantfile_id']).one_or_none()
        if result is not None:
            return json.loads(str(result))
    return None

def delete_variantfile(variantfile_id):
    with Session() as session:
        new_object = session.query(VariantFile).filter_by(id=variantfile_id).one()
        session.delete(new_object)
        session.commit()
        return json.loads(str(new_object))


def list_variantfiles():
    with Session() as session:
        result = session.query(VariantFile).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def get_sample(sample_id):
    with Session() as session:
        result = session.query(Sample).filter_by(sample_id=sample_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_sample(obj):
    # obj = {'id', 'variantfile_id'}
    with Session() as session:
        new_sample = session.query(Sample).filter_by(sample_id=obj['id'], variantfile_id=obj['variantfile_id']).one_or_none()
        if new_sample is None:
            new_sample = Sample()
        new_sample.sample_id = obj['id']
        new_sample.variantfile_id = obj['variantfile_id']
        session.add(new_sample)
        session.commit()
        result = session.query(Sample).filter_by(sample_id=obj['id'], variantfile_id=obj['variantfile_id']).one_or_none()
        if result is not None:
            return json.loads(str(result))
        return None


def delete_sample(id_):
    with Session() as session:
        new_object = session.query(Sample).filter_by(id=id_).one()
        session.delete(new_object)
        session.commit()
        return json.loads(str(new_object))


def list_samples():
    with Session() as session:
        result = session.query(Sample).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def get_samples_in_drs_objects(obj):
    # obj = {'drs_object_ids'}
    with Session() as session:
        result = []
        q = select(Sample.sample_id).where(Sample.variantfile_id.in_(set(obj['drs_object_ids']))).distinct()
        for row in session.execute(q):
            result.append(str(row._mapping['sample_id']))
        return result


def get_headers(obj):
    # obj = {'text', 'variantfile_id'}
    with Session() as session:
        new_obj = []
        q = select(Header.text)
        if "text" in obj:
            q = q.like(Header.text)
        if "variantfile_id" in obj:
            q = q.where(Header.associated_variantfiles.any(VariantFile.id == obj['variantfile_id']))
        for r in session.execute(q):
            for k in r._mapping.values():
                new_obj.append(k)
        return new_obj


def add_header_for_variantfile(obj):
    # obj = {'text' or 'texts', 'variantfile_id'}
    headertexts = []
    if 'text' in obj:
        headertexts.append(obj['text'].strip())
    elif 'texts' in obj:
        headertexts = map(lambda x: x.strip(), obj['texts'])
    with Session() as session:
        new_variantfile = session.query(VariantFile).filter_by(id=obj['variantfile_id']).one_or_none()
        for headertext in headertexts:
            if headertext == '' or headertext.startswith("#CHROM"):
                continue
            q = select(Header).filter_by(text=headertext).limit(1)
            new_header = session.scalars(q).first()

            if new_header is None:
                new_header = Header()
                new_header.text = headertext
            new_header.associated_variantfiles.append(new_variantfile)
            session.add(new_header)
        session.commit()
    return None


def delete_header(text):
    with Session() as session:
        new_object = session.query(Header).filter_by(text=text).one()
        session.delete(new_object)
        session.commit()
        return json.loads(str(new_object))


# for efficiency, positions are bucketed into 10 bp sets: pos_bucket_id == base pair position/10, rounded down
def get_bucket_for_position(pos):
    return int(pos/BUCKET_SIZE) * BUCKET_SIZE


def create_pos_bucket(obj):
    # obj = { 'variantfile_id',
    #         'pos_bucket_ids',
    #         'bucket_counts',
    #         'normalized_contigs'
    #       }
    with Session() as session:
        pos_bucket_ids = obj['pos_bucket_ids']
        contig_ids = obj['normalized_contigs']
        bucket_counts = obj['bucket_counts']
        variantfile_id = obj['variantfile_id']
        new_variantfile = session.query(VariantFile).filter_by(id=variantfile_id).one_or_none()
        if new_variantfile is None:
            return None
        curr_contig = None
        for i in range(len(pos_bucket_ids)):
            pos_bucket_id = pos_bucket_ids[i]
            contig_id = contig_ids[i]
            bucket_count = bucket_counts[i]
            if bucket_count > 0:
                if curr_contig is None or curr_contig.id != contig_id:
                    curr_contig = session.query(Contig).filter_by(id=contig_id).one_or_none()
                    if curr_contig is not None:
                        curr_contig.associated_variantfiles.append(new_variantfile)
                        session.add(curr_contig)
                new_pos_bucket = session.query(PositionBucket).filter_by(pos_bucket_id=pos_bucket_id, contig_id=contig_id).one_or_none()
                if new_pos_bucket is None:
                    new_pos_bucket = PositionBucket()
                    new_pos_bucket.pos_bucket_id = pos_bucket_id
                    new_pos_bucket.contig_id = contig_id
                    session.add(new_pos_bucket)
                    session.commit()
                association = session.query(PositionBucketVariantFileAssociation).filter_by(pos_bucket_id=new_pos_bucket.id, variantfile_id=variantfile_id).one_or_none()
                if association is None:
                    association = PositionBucketVariantFileAssociation()
                    association.pos_bucket_id = new_pos_bucket.id
                    association.variantfile_id = variantfile_id
                    association.bucket_count = 0
                association.bucket_count = bucket_count
                session.add(association)
                session.commit()
        return None


def delete_pos_bucket(pos_bucket_id, normalized_contig_id):
    with Session() as session:
        new_object = session.query(PositionBucket).filter_by(id=pos_bucket_id, contig_id=normalized_contig_id).one()
        session.delete(new_object)
        session.commit()
        return json.loads(str(new_object))


def get_pos_bucket(pos_bucket_id, contig_id):
    with Session() as session:
        alias = session.query(Alias).filter_by(id=contig_id).one_or_none()
        result = session.query(PositionBucket).filter_by(id=pos_bucket_id, contig_id=alias.contig_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def list_pos_buckets():
    with Session() as session:
        result = session.query(PositionBucket).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def get_variant_count_for_variantfile(obj):
    # obj = {id, referenceName, start, end}
    with Session() as session:
        vfile = aliased(VariantFile)
        q = select(vfile.drs_object_id, PositionBucket.id, PositionBucket.pos_bucket_id, PositionBucketVariantFileAssociation.bucket_count).select_from(PositionBucket).join(PositionBucketVariantFileAssociation).where(vfile.drs_object_id == PositionBucketVariantFileAssociation.variantfile_id).where(vfile.drs_object_id == obj['id'])
        if 'referenceName' in obj and obj['referenceName'] is not None:
            contig_id = normalize_contig(obj['referenceName'])
            q = q.where(PositionBucket.contig_id == contig_id)
        if 'start' in obj and obj['start'] > 0:
            q = q.where(PositionBucket.pos_bucket_id >= obj['start'])
        if 'end' in obj and obj['end'] != -1:
            q = q.where(PositionBucket.pos_bucket_id < obj['end'])
        q = q.distinct()
        result = []
        #"('drs_object_id', 'id', 'pos_bucket_id')"
        for row in session.execute(q):
            #return str(row._fields)
            result.append({'pos_bucket': row._mapping['pos_bucket_id'], 'count': row._mapping['bucket_count']})
        return result


def normalize_contig(contig_id):
    with Session() as session:
        contig = session.query(Contig).filter_by(id=contig_id).one_or_none()
        if contig is not None:
            return contig.id
        alias = session.query(Alias).filter_by(id=contig_id).one_or_none()
        if alias is not None:
            return alias.contig_id
        else:
            return None


def get_contig_prefix(contig_id):
    normalized_contig = normalize_contig(contig_id)
    suffix = normalized_contig.replace("chr", "")
    prefix = contig_id.replace(suffix, "")
    return prefix


def get_contig_name_in_variantfile(obj):
    # obj = { 'refname', 'variantfile_id' }
    normalized = normalize_contig(obj['refname'])
    varfile = get_variantfile(obj['variantfile_id'])
    return varfile['chr_prefix'] + normalized


def search(obj, tries=1):
    # obj = {'region', 'headers'}
    if tries > 3:
        raise Exception(f"Exception in search, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    with Session() as session:
        try:
            vfile = aliased(VariantFile)
            q = select(vfile.drs_object_id, vfile.reference_genome, PositionBucket.id, PositionBucket.pos_bucket_id).select_from(PositionBucket).join(vfile.associated_pos_buckets).join(vfile.associated_headers)
            if 'headers' in obj:
                for header in obj['headers']:
                    q = q.where(Header.text.like(f"%{header}%"))
            if 'region' in obj:
                if 'referenceName' in obj['region']:
                    contig_id = normalize_contig(obj['region']['referenceName'])
                    q = q.where(PositionBucket.contig_id == contig_id)
                else:
                    return {"error": "no referenceName specified"}
                if 'start' in obj['region']:
                    q = q.where(PositionBucket.pos_bucket_id >= get_bucket_for_position(obj['region']['start']))
                if 'end' in obj['region']:
                    q = q.where(PositionBucket.pos_bucket_id <= get_bucket_for_position(obj['region']['end']))
            q = q.distinct()
            drs_obj_ids = set()
            pos_bucket_ids = set()
            raw_result = {}
            results = []
            for row in session.execute(q):
                drs_obj = row._mapping['drs_object_id']
                if drs_obj not in raw_result:
                    raw_result[drs_obj] = []
                raw_result[drs_obj].append(row._mapping['id'])
            for drs_obj in raw_result.keys():
                curr_result = {'drs_object_id': drs_obj, 'variantcount': 0}
                curr_result['reference_genome'] = session.query(VariantFile).filter_by(id=drs_obj).one_or_none().reference_genome
                bvs = session.query(PositionBucketVariantFileAssociation).where(PositionBucketVariantFileAssociation.pos_bucket_id.in_(raw_result[drs_obj])).where(PositionBucketVariantFileAssociation.variantfile_id == drs_obj).all()
                if bvs is not None:
                    for bv in bvs:
                        curr_result['variantcount'] += bv.bucket_count
                results.append(curr_result)
            return results
        except Exception as e:
            app.logger.info(f"Exception in search: {str(e)}, trying again")
            return search(obj, tries=tries+1)
    return None