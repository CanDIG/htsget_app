from sqlalchemy.orm import relationship, aliased
from sqlalchemy import Column, Integer, String, JSON, Boolean, MetaData, ForeignKey, Table, select
import json
import os
import re
from datetime import datetime
from random import randint
from time import sleep
from config import BUCKET_SIZE, HTSGET_URL, MAX_TRIES
from flask import Flask
from candigv2_logging.logging import CanDIGLogger
from server import Session, ObjectDBBase
import requests
from authx.auth import create_service_token

logger = CanDIGLogger(__file__)


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

    def __repr__(self):
        result = {
            'id': self.id,
            'aliases': [],
            'associated_variantfiles': [],
            'pos_buckets': []
        }
        for alias in self.aliases:
            result['aliases'].append(alias.id)
        for varfile_assoc in self.associated_variantfiles:
            result['associated_variantfiles'].append(varfile_assoc.id)
        for x in self.pos_buckets:
            result['pos_buckets'].append(x.id)

        return json.dumps(result)



class VariantFile(ObjectDBBase):
    __tablename__ = 'variantfile'
    id = Column(String, primary_key=True)
    indexed = Column(Integer)
    chr_prefix = Column(String)
    reference_genome = Column(String)

    # a variantfile maps to a drs object
    drs_object_id = Column(String)

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
    pos_bucket_id = Column(Integer, primary_key=True) # each bucket contains 10 bp of positions
    # a pos_bucket is part of a single contig
    contig_id = Column(String, ForeignKey('contig.id'), primary_key=True)
    id = Column(Integer)

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
            'contig_id': self.contig_id,
            'pos_bucket_id': self.pos_bucket_id,
            'variantfiles': []
        }
        for varfile_assoc in self.associated_variantfiles:
            result['variantfiles'].append(varfile_assoc.id)

        return json.dumps(result)


# these are samples in variantfiles
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
    if tries > MAX_TRIES:
        raise Exception(f"Exception in get_variantfile {variantfile_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        with Session() as session:
            result = session.query(VariantFile).filter_by(id=variantfile_id).one_or_none()
            if result is not None:
                new_obj = json.loads(str(result))
                return new_obj
    except Exception as e:
        logger.debug(f"Exception in get_variantfile {variantfile_id}: {str(e)}, trying again")
        return get_variantfile(variantfile_id, tries=tries+1)
    return None


def create_variantfile(obj, tries=1):
    # obj = {"id", "reference_genome"}
    if tries > MAX_TRIES:
        raise Exception(f"Exception in create_variantfile {obj['id']}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        with Session() as session:
            new_variantfile = session.query(VariantFile).filter_by(id=obj['id']).one_or_none()
            if new_variantfile is None:
                new_variantfile = VariantFile()
                new_variantfile.indexed = 0
                new_variantfile.chr_prefix = ''
            new_variantfile.id = obj['id']
            new_variantfile.reference_genome = obj['reference_genome']
            headers = {
                "X-Service-Token": create_service_token()
            }
            resp = requests.get(url=f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/objects/{obj['id']}", headers=headers)
            if resp.status_code == 200:
                new_variantfile.drs_object_id = obj['id']
            else:
                raise Exception(f"Cannot create variantfile {obj['id']}: no corresponding DRS object")
            session.add(new_variantfile)
            session.commit()
            result = session.query(VariantFile).filter_by(id=obj['id']).one_or_none()
            if result is not None:
                return json.loads(str(result))
    except Exception as e:
        logger.debug(f"Exception in create_variantfile {obj['id']}: {str(e)}, trying again")
        return create_variantfile(obj, tries=tries+1)
    return None


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


def create_pos_buckets_for_variantfile(obj):
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
            logger.debug(f"couldn't find variantfile {variantfile_id}")
            return None # we can't work on nonexistent variantfiles

        # find all of the contigs that need to be updated
        contigs_to_update = {}
        for contig_id in contig_ids:
            # add the variantfile to the contigs to update
            if contig_id not in contigs_to_update:
                contigs_to_update[contig_id] = set()
            contigs_to_update[contig_id].add(new_variantfile)

        # update the 25 contigs
        for contig_id in contigs_to_update.keys():
            curr_contig = session.query(Contig).filter_by(id=contig_id).one_or_none()
            if curr_contig is not None:
                curr_contig.associated_variantfiles.extend(contigs_to_update[contig_id])
                session.add(curr_contig)
        session.commit()

        # find all of the pos buckets that need to be accessed
        buckets_needed_by_contig = {}
        for i in range(len(pos_bucket_ids)):
            pos_bucket_id = pos_bucket_ids[i]
            contig_id = contig_ids[i]
            bucket_count = bucket_counts[i]
            if bucket_count > 0:
                if contig_id not in buckets_needed_by_contig:
                    buckets_needed_by_contig[contig_id] = set()
                buckets_needed_by_contig[contig_id].add(pos_bucket_id)

        # search for the resulting buckets: if not there, insert
        existing_bucket_ids = {}
        for contig_id in buckets_needed_by_contig.keys():
            existing_buckets_in_contig = session.query(PositionBucket).filter(PositionBucket.pos_bucket_id.in_(list(buckets_needed_by_contig[contig_id])), PositionBucket.contig_id==contig_id).all()
            existing_bucket_ids[contig_id] = (list(map(lambda x: x.pos_bucket_id, existing_buckets_in_contig)))

        new_pos_buckets = []
        for i in range(len(pos_bucket_ids)):
            pos_bucket_id = pos_bucket_ids[i]
            contig_id = contig_ids[i]
            if pos_bucket_id not in existing_bucket_ids[contig_id]:
                new_pos_buckets.append({'pos_bucket_id': int(pos_bucket_id), 'contig_id': contig_id})
        session.bulk_insert_mappings(PositionBucket, new_pos_buckets)
        session.commit()

    # remove any existing PositionBucketVariantFileAssociations:
    with Session() as session:
        session.query(PositionBucketVariantFileAssociation).filter(PositionBucketVariantFileAssociation.variantfile_id==variantfile_id).delete()
        session.commit()

    with Session() as session:
        # # okay now all of the buckets exist: let's find the ones we need
        existing_buckets = []
        for contig_id in buckets_needed_by_contig.keys():
            existing_buckets.extend(session.query(PositionBucket).filter(PositionBucket.pos_bucket_id.in_(list(buckets_needed_by_contig[contig_id])), PositionBucket.contig_id==contig_id).all())

        # sort bucket IDs for quick access
        bucket_hash = {}
        for bucket in existing_buckets:
            if bucket.contig_id not in bucket_hash:
                bucket_hash[bucket.contig_id] = {}
            if bucket.pos_bucket_id not in bucket_hash[bucket.contig_id]:
                bucket_hash[bucket.contig_id][bucket.pos_bucket_id] = bucket.id

        pbvfs_to_add = []

        for i in range(len(pos_bucket_ids)):
            pos_bucket_id = pos_bucket_ids[i]
            contig_id = contig_ids[i]
            bucket_count = bucket_counts[i]

            # only need to update buckets that have a count greater than 0
            if bucket_count > 0:
                bucket_id = bucket_hash[contig_id][pos_bucket_id]
                pbvfs_to_add.append({'pos_bucket_id': int(bucket_id), 'variantfile_id': variantfile_id, 'bucket_count': int(bucket_count)})

        session.bulk_insert_mappings(PositionBucketVariantFileAssociation, pbvfs_to_add)
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
    if tries > MAX_TRIES:
        raise Exception(f"Exception in search, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        with Session() as session:
            vfile = aliased(VariantFile)
            q = select(vfile.drs_object_id, vfile.reference_genome, PositionBucket.id, PositionBucket.pos_bucket_id).select_from(PositionBucket).join(vfile.associated_pos_buckets)
            if 'headers' in obj:
                q = q.join(vfile.associated_headers)
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
        logger.debug(f"Exception in search: {str(e)}, trying again")
        return search(obj, tries=tries+1)
    return None