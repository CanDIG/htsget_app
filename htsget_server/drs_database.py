from sqlalchemy.orm import relationship, aliased, declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, JSON, Boolean, MetaData, ForeignKey, Table, select, create_engine
import json
import re
from datetime import datetime
from random import randint
from time import sleep
from config import BUCKET_SIZE, HTSGET_URL, MAX_TRIES, DRS_DB_PATH
from flask import Flask
from candigv2_logging.logging import CanDIGLogger
import database

logger = CanDIGLogger(__file__)


engine = create_engine(DRS_DB_PATH, echo=False, pool_timeout=5, pool_size=10)
ObjectDBBase = declarative_base()
ObjectDBBase.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


## CanDIG programs entities
class Program(ObjectDBBase):
    __tablename__ = 'program'
    id = Column(String, primary_key=True)
    associated_drs = relationship("DrsObject", back_populates="program", cascade="all, delete, delete-orphan")
    statistics = Column(JSON)
    def __repr__(self):
        result = {
            'id': self.id,
            'drsobjects': []
        }
        if self.statistics is not None:
            result['statistics'] = self.statistics
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
    program_id = Column(String, ForeignKey('program.id'))
    program = relationship("Program", back_populates="associated_drs")
    meta_data = Column(JSON)

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
        else:
            result['contents'] = []
        if len(list(self.access_methods)) > 0:
            result['access_methods'] = json.loads(self.access_methods.__repr__())
        if self.program is not None:
            result['program'] = self.program_id
        if self.meta_data is not None:
            result['metadata'] = self.meta_data
            if 'indexed' in result['metadata']:
                result['indexed'] = result['metadata']['indexed']
            if 'reference' in result['metadata']:
                result['reference_genome'] = result['metadata']['reference']
        else:
            result['metadata'] = {}
        return json.dumps(result)


class AccessMethod(ObjectDBBase):
    __tablename__ = 'access_method'
    id = Column(Integer, primary_key=True)
    drs_object_id = Column(String, ForeignKey('drs_object.id'))
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
    drs_object_id = Column(String, ForeignKey('drs_object.id'))
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


""" Helper Functions"""
def get_drs_object(object_id, expand=False, tries=1):
    if tries > MAX_TRIES:
        raise Exception(f"Exception in get_drs_object {object_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        with Session() as session:
            result = session.query(DrsObject).filter_by(id=object_id).one_or_none()
            if result is not None:
                new_obj = json.loads(str(result))
    #         if expand:
    #             expand doesn't do anything on this DRS server
                return new_obj
    except Exception as e:
        logger.debug(f"Exception in get_drs_object {object_id}: {str(e)}, trying again")
        return get_drs_object(object_id, expand, tries=tries+1)
    return None


def list_drs_objects(program_id=None, submitter_sample_id=None):
    with Session() as session:
        if program_id is None and submitter_sample_id is None:
            result = session.query(DrsObject).all()
        elif submitter_sample_id is None: # searching for program
            result = session.query(DrsObject).filter_by(program_id=program_id).all()
        else: # searching for experiments with sample registration IDs
            result = session.query(DrsObject).filter_by(name=submitter_sample_id).all()

        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_drs_object(obj, tries=1):
    logger.debug(f"create_drs_object {obj['id']}")
    if tries > MAX_TRIES:
        raise Exception(f"Exception in create_drs_object {obj['id']}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
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
            if 'metadata' in obj:
                new_object.meta_data = obj['metadata']
            if 'program' in obj:
                program = session.query(Program).filter_by(id=obj['program']).one_or_none()
                if program is None:
                    create_program({"id": obj["program"], "drsobjects": []})
                new_object.program_id = obj['program']

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

            result = session.query(DrsObject).filter_by(id=obj['id']).one_or_none()
            logger.debug(f"DONE create_drs_object {obj['id']}")
            return json.loads(str(result))
    except Exception as e:
        logger.debug(f"Exception in create_drs_object {obj['id']}: {str(e)}, trying again")
        return create_drs_object(obj, tries=tries+1)


def delete_drs_object(obj_id, tries=1):
    if tries > MAX_TRIES:
        raise Exception(f"Exception in delete_drs_object {obj_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        with Session() as session:
            new_object = session.query(DrsObject).filter_by(id=obj_id).one()
            program = session.query(Program).filter_by(id=new_object.program_id).one_or_none()
            #if new_object.description in ["variant"]:
                # this is a AnalysisDrsObject; we need to delete any indexed variantfiles
                # variantfiles = session.query(VariantFile).filter_by(drs_object_id=new_object.id).all()
                # for vf in variantfiles:
                #     session.delete(vf)
                #     session.commit()
            session.delete(new_object)
            session.commit()
            return json.loads(str(new_object))
    except Exception as e:
        logger.debug(f"Exception in delete_drs_object {obj_id}: {str(e)}, trying again")
        return delete_drs_object(obj_id, tries=tries+1)
    return None


def get_program(program_id):
    with Session() as session:
        result = session.query(Program).filter_by(id=program_id).one_or_none()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def list_programs():
    with Session() as session:
        result = session.query(Program).all()
        if result is not None:
            new_obj = json.loads(str(result))
            return new_obj
        return None


def create_program(obj, tries=1):
    if tries > MAX_TRIES:
        raise Exception(f"Exception in create_program {obj['id']}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        with Session() as session:
            new_program = session.query(Program).filter_by(id=obj['id']).one_or_none()
            if new_program is None:
                new_program = Program()
            if "statistics" in obj:
                new_program.statistics = obj["statistics"]
            else:
                new_program.statistics = {}
            new_program.id = obj['id']
            for drs_uri in obj['drsobjects']:
                new_drs = session.query(DrsObject).filter_by(self_uri=drs_uri).one_or_none()
                if new_drs is not None:
                    new_program.associated_drs.append(new_drs)
            session.add(new_program)
            session.commit()
            result = session.query(Program).filter_by(id=obj['id']).one_or_none()
            if result is not None:
                return json.loads(str(result))
    except Exception as e:
        logger.debug(f"Exception in create_program {obj['id']}: {str(e)}, trying again")
        return create_program(obj, tries=tries+1)
    return None


def delete_program(program_id, tries=1):
    if tries > MAX_TRIES:
        raise Exception(f"Exception in delete_program {program_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        with Session() as session:
            program_objs = session.query(Program).filter_by(id=program_id).all()
            for program_obj in program_objs:
                for drs_obj in program_obj.associated_drs:
                    session.delete(drs_obj)
                    session.commit()
                session.delete(program_obj)
                session.commit()
            session.commit()
            return json.loads(str(program_objs))
    except Exception as e:
        logger.debug(f"Exception in delete_program {program_id}: {str(e)}, trying again")
        return delete_program(program_id, tries=tries+1)
    return None


