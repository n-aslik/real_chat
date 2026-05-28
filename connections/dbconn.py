from lib.config import configdb
from pypika import NULL, Schema
from pypika import PostgreSQLQuery as Q
from pypika import Table, Field, Tuple
from pypika import Case, functions as fn
from fastapi import HTTPException
from psycopg2 import pool
from contextlib import contextmanager

pg_pool = pool.ThreadedConnectionPool(1, 50, **configdb())

@contextmanager
def connection():
    try:
        con = pg_pool.getconn()
        cur = con.cursor()
        yield cur
        con.commit()
    except Exception as e:
        con.rollback()
        cur.close()
        # send to logger
        print("db error: {}".format(e))
        raise HTTPException(status_code=409, detail="db error: {}".format(e))
    finally:
        cur.close()
        pg_pool.putconn(con)

class DB(object):
    
    __instance = None

    information_schema=Schema("information_schema")
    pg_catalog=Schema("pg_catalog")
    table_schema=Field("table_schema")
    table_name=Field("table_name")
    column_name=Field("column_name")
    ordinal_position=Field("ordinal_position")
    data_type=Field("data_type")
    is_nullable=Field("is_nullable")
    column_default=Field("column_default")
    character_maximum_length=Field("character_maximum_length")
    numeric_precision=Field("numeric_precision")
    max_length="max_length"

    structure = None

    @staticmethod 
    def get_instance():
        """ Static access method. """
        if DB.__instance == None:
            DB()
        return DB.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if DB.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            DB.__instance = self
    
    @staticmethod
    def get_structure():
        if DB.structure == None:
            with connection() as cur:
                DB.structure = {}  

                query = Q.from_(DB.information_schema.columns).select(
                        DB.table_schema,
                        DB.table_name,
                        DB.ordinal_position,
                        DB.column_name,
                        DB.data_type,
                        Case()
                            .when(DB.character_maximum_length.notnull(), DB.character_maximum_length)
                            .else_(DB.numeric_precision).as_(DB.max_length),
                        DB.is_nullable,
                        DB.column_default
                    ).where(
                        DB.table_schema.notin(Tuple("information_schema", "pg_catalog"))
                    ).orderby(
                        DB.table_schema, 
                        DB.table_name, 
                        DB.ordinal_position
                    )

                cur.execute(query.get_sql())
                rows = cur.fetchall()

                for row in rows:
                    if (not(row[0] in DB.structure)):
                        DB.structure[row[0]] = {}
                    if (not(row[1] in DB.structure[row[0]])):
                        DB.structure[row[0]][row[1]] = {}

                    DB.structure[row[0]][row[1]][row[3]] = None

        return DB.structure

def dbstructure(func):
    def wrapper(*args, **kwargs):
        structure = DB.get_instance().get_structure().copy()
        return func(structure, *args, **kwargs)
    return wrapper


  


    
    


    

