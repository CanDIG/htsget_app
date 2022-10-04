from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import Column, Integer, String, MetaData, ForeignKey, Table, create_engine
import json
from datetime import datetime
from config import DB_PATH


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


class VariantFile(ObjectDBBase):
    __tablename__ = 'variantfile'
    id = Column(Integer, primary_key=True)

    # a variantfile maps to a drs object
    drs_object_id = Column(Integer, ForeignKey('drs_object.id'))
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
    
    # a variantfile can contain many headers
    associated_headers = relationship("Header",
        secondary=header_variantfile_association,
        back_populates="associated_variantfiles"
    )
    
    # a variantfile can contain several samples
    samples = relationship(
        "Sample",
        back_populates="variantfile"
    )


class Position(ObjectDBBase):
    __tablename__ = 'position'
    id = Column(Integer, primary_key=True)
    
    # a position is part of a single contig
    contig_id = Column(String, ForeignKey('contig.id'))
    contig = relationship(
        "Contig",
        back_populates="position",
        uselist=False
    )


class Sample(ObjectDBBase):
    __tablename__ = 'sample'
    id = Column(String, primary_key=True)
    
    # a sample is in a single variantfile
    variantfile_id = Column(String, ForeignKey('variantfile.id'))
    variantfile = relationship(
        "VariantFile",
        back_populates="sample",
        uselist=False
    )


class Header(ObjectDBBase):
    __tablename__ = 'header'
    id = Column(Integer, primary_key=True)
    text = Column(String, primary_key=True)
    
    # a header is in many variantfiles
    associated_variantfiles = relationship("Variant",
        secondary=header_variantfile_association,
        back_populates="associated_variantfiles"
    )


## CanDIG datasets entities
dataset_association = Table(
    'dataset_association', ObjectDBBase.metadata,
    Column('dataset_id', ForeignKey('dataset.id'), primary_key=True),
    Column('drs_object_id', ForeignKey('drs_object.id'), primary_key=True)
)


class Dataset(ObjectDBBase):
    __tablename__ = 'dataset'
    id = Column(String, primary_key=True)
    associated_drs = relationship("DrsObject",
        secondary=dataset_association,
        back_populates="associated_datasets"
    )
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
    contents = relationship("ContentsObject")
    associated_datasets = relationship(
        'Dataset',
        secondary=dataset_association,
        back_populates='associated_drs'
    )

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
            'aliases': json.loads(self.aliases),
            'datasets': []
        }
        if len(list(self.contents)) > 0:
            result['contents'] = json.loads(self.contents.__repr__())
        if len(list(self.access_methods)) > 0:
            result['access_methods'] = json.loads(self.access_methods.__repr__())
        for drs_assoc in self.associated_datasets:
            result['datasets'].append(drs_assoc.id)
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
        if self.region is not "":
            result['region'] = self.region
        if self.url is not "":
            result['access_url'] = {
                'url': self.url,
                'headers': json.loads(self.headers)
            }
        if self.access_id is not "":
            result['access_id'] = self.access_id

        return json.dumps(result)


class ContentsObject(ObjectDBBase):
    __tablename__ = 'content_object'
    id = Column(Integer, primary_key=True)
    drs_object_id = Column(Integer, ForeignKey('drs_object.id'))
    drs_object = relationship("DrsObject", back_populates="contents")
    name = Column(String, default='') # like a filename
    drs_uri = Column(String, default='[]') # JSON array of strings of DRS id URIs
    contents = Column(String, default='[]') # JSON array of ContentsObject.ids
    def __repr__(self):
        result = {
            'name': self.name,
            'drs_uri': json.loads(self.drs_uri)
        }
        if len(json.loads(self.contents)) > 0:
            result['contents'] = json.loads(self.contents)

        return json.dumps(result)
    
    
ObjectDBBase.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


""" Helper Functions"""
def get_drs_object(object_id, expand=False):
    with Session() as session:
        result = session.query(DrsObject).filter_by(id=object_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
#         if expand:
#             expand doesn't do anything on this DRS server
            return new_obj
        return None


def list_drs_objects():
    with Session() as session:
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
        if 'self_uri' in obj:
            new_object.self_uri = obj['self_uri']
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
        for contents in obj['contents']:
            new_contents = ContentsObject()
            new_contents.drs_object_id = new_object.id
            new_contents.name = contents['name']
            if 'drs_uri' in contents:
                new_contents.drs_uri = json.dumps(contents['drs_uri'])
            if 'contents' in contents:
                new_contents.contents = json.dumps(contents['contents'])
            session.add(new_contents)
        session.add(new_object)
        session.commit()
        result = session.query(DrsObject).filter_by(id=obj['id']).one_or_none()
        return json.loads(str(result))


def delete_drs_object(obj_id):
    with Session() as session:
        new_object = session.query(DrsObject).filter_by(id=obj_id).one()
        session.delete(new_object)
        session.commit()
        return json.loads(str(new_object))


def get_dataset(dataset_id):
    with Session() as session:
        result = session.query(Dataset).filter_by(id=dataset_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def list_datasets():
    with Session() as session:
        result = session.query(Dataset).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_dataset(obj):
    with Session() as session:
        new_dataset = session.query(Dataset).filter_by(id=obj['id']).one_or_none()
        if new_dataset is None:
            new_dataset = Dataset()
        new_dataset.id = obj['id']
        for drs_uri in obj['drsobjects']:
            new_drs = session.query(DrsObject).filter_by(self_uri=drs_uri).one_or_none()
            if new_drs is not None:
                new_dataset.associated_drs.append(new_drs)
        session.add(new_dataset)
        session.commit()
        result = session.query(Dataset).filter_by(id=obj['id']).one_or_none()
        if result is not None:
            return json.loads(str(result))
        return None


def delete_dataset(dataset_id):
    with Session() as session:
        new_object = session.query(Dataset).filter_by(id=dataset_id).one()
        session.delete(new_object)
        session.commit()
        return json.loads(str(new_object))


def get_variantfile(variantfile_id):
    with Session() as session:
        result = session.query(VariantFile).filter_by(id=variantfile_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_variantfile(obj):
    with Session() as session:
        new_variantfile = session.query(VariantFile).filter_by(id=obj['id']).one_or_none()
        if new_variantfile is None:
            new_variantfile = VariantFile()
        new_variantfile.id = obj['id']
        new_drs = session.query(DrsObject).filter_by(self_uri=obj['id']).one_or_none()
        if new_drs is not None:
            new_variantfile.drs_object_id = new_drs.id
        session.add(new_variantfile)
        session.commit()
        result = session.query(VariantFile).filter_by(id=obj['id']).one_or_none()
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
        result = session.query(Sample).filter_by(id=sample_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_sample(obj):
    with Session() as session:
        new_sample = session.query(Sample).filter_by(id=obj['id']).one_or_none()
        if new_sample is None:
            new_sample = Sample()
        new_sample.id = obj['id']
        new_variantfile = session.query(VariantFile).filter_by(self_uri=obj['variantfile_id']).one_or_none()
        if new_variantfile is not None:
            new_sample.variantfile_id = new_variantfile.id
        session.add(new_sample)
        session.commit()
        result = session.query(Sample).filter_by(id=obj['id']).one_or_none()
        if result is not None:
            return json.loads(str(result))
        return None


def delete_sample(sample_id):
    with Session() as session:
        new_object = session.query(Sample).filter_by(id=sample_id).one()
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
