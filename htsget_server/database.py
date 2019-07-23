from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey

SQLITE = 'sqlite'

class MyDatabase:
    # http://docs.sqlalchemy.org/en/latest/core/engines.html
    DB_ENGINE = {
        SQLITE: 'sqlite:///{DB}'
    }

    # Main DB Connection Ref Obj
    db_engine = None
    def __init__(self, dbtype, username='', password='', dbname=''):
        dbtype = dbtype.lower()
        if dbtype in self.DB_ENGINE.keys():
            engine_url = self.DB_ENGINE[dbtype].format(DB=dbname)
            self.db_engine = create_engine(engine_url)
        else:
            print("DBType is not found in DB_ENGINE")
            print("DBType is not found in DB_ENGINE")


    def create_db_table(self):
        metadata = MetaData()
        files = Table('files', metadata,
                        Column('id', String, primary_key=True),
                        Column('file_type', String),
                        Column('format', String)
                        )
        try:
            metadata.create_all(self.db_engine)
            print("Table created")
        except Exception as e:
            print("Error occurred during Table creation!")
            print(e)
    

    def execute(self, query, param):
        """
        Execute query to insert, update, or delete from DB
        """
        if query == '' : return
        with self.db_engine.connect() as connection:
            try:
                result = connection.execute(query, param)
            except Exception as e:
                print(e)
    

    def get_data(self, query, param):
        if query == '' : return
        with self.db_engine.connect() as connection:
            try:
                result = connection.execute(query, param)
            except Exception as e:
                print(e)
            else:
                res = []
                for row in result:
                    res.append(row)
                return res
    

    def print_all_data(self, table='', query=''):
        query = query if query != '' else "SELECT * FROM '{}';".format('files')
        print(query)
        with self.db_engine.connect() as connection:
            try:
                result = connection.execute(query)
            except Exception as e:
                print(e)
            else:
                for row in result:
                    print(row) # print(row[0], row[1], row[2])
                result.close()
        print("\n")