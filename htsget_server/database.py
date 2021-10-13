from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import Column, Integer, String, MetaData, ForeignKey, create_engine
import configparser
import json
from pathlib import Path
from datetime import datetime

config = configparser.ConfigParser()
config.read(Path('./config.ini'))
DB_PATH = config['paths']['DBPath']

engine = create_engine(DB_PATH)

ObjectDBBase = declarative_base()


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
