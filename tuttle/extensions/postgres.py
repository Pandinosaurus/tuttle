# -*- coding: utf8 -*-

from re import compile
from tuttle.resources import MalformedUrl, ResourceMixIn
from hashlib import sha1
import psycopg2

class PostgreSQLResource(ResourceMixIn, object):
    """A resource for an object in a PostgreSQL database. Objects can be tables, view..."""
    """eg : pg://localhost:5432/tuttle_test_database/test_schema/test_table"""
    scheme = 'postgres'

    __ereg = compile("^pg://([^/^:]*)(:[0-9]*)?/([^/]*)/([^/]*/)?([^/]*)$")

    def __init__(self, url):
        super(PostgreSQLResource, self).__init__(url)
        m = self.__ereg.match(url)
        if m is None:
            raise MalformedUrl("Malformed PostgreSQL url : '{}'".format(url))
        self._server = m.group(1)
        captured_port = m.group(2)
        if captured_port:
            self._port = captured_port[1:]
        else:
            self._port = None
        self._database = m.group(3)
        captured_schema = m.group(4)
        if captured_schema:
            self._schema = m.group(4)[:-1]
        else:
            self._schema = "public"
        self._objectname = m.group(5)

    def pg_object_type(self, db, schema, objectname):
        """Returns the type of object in the database
         * 'r' for tables
         * 'v' for views
        """
        cur = db.cursor()
        query = """SELECT c.relname, c.relkind, n.nspname AS schema
                     FROM pg_class c
                       LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE relname=%s AND n.nspname=%s
        """
        cur.execute(query, (objectname, schema, ))
        row = cur.fetchone()
        if row:
            return row[1]

    def exists(self):
        try:
            conn_string = "host=\'{}\' dbname='{}' port={} user=tuttle password=tuttle".format(self._server, self._database,
                                                                   self._port)
            db = psycopg2.connect(conn_string)
        except psycopg2.OperationalError:
            return False
        try:
            result = self.pg_object_type(db, self._schema, self._objectname) is not None
        except psycopg2.OperationalError:
            return False
        finally:
            db.close()
        return result

    def remove_table(self, cur):
        cur.execute('DROP TABLE "{}"."{}" CASCADE'.format(self._schema, self._objectname))

    def remove_view(self, cur):
        cur.execute('DROP VIEW "{}"."{}" CASCADE'.format(self._schema, self._objectname))

    def remove(self):
        try:
            conn_string = "host=\'{}\' dbname='{}' port={} user=tuttle password=tuttle".format(self._server, self._database,
                                                                   self._port)
            db = psycopg2.connect(conn_string)
        except psycopg2.OperationalError:
            return False
        try:
            cur = db.cursor()
            obj_type = self.pg_object_type(db, self._schema, self._objectname)
            if obj_type == 'r':
                self.remove_table(cur)
            elif obj_type == 'v':
                self.remove_view(cur)
            db.commit()
        finally:
            db.close()

    def table_signature(self, db, schema, tablename):
        """Generate a hash for the contents of a table."""
        checksum = sha1()
        cur = db.cursor()
        query = """SELECT *
                    FROM information_schema.columns
                    WHERE table_name=%s AND table_schema=%s
                    ORDER BY column_name;
                """
        cur.execute(query, (tablename, schema))
        for row in cur:
            for field in row:
                checksum.update(str(field))
        cur.execute('SELECT * FROM "{}"'.format(tablename))
        for row in cur:
            for field in row:
                checksum.update(str(field))
        return checksum.hexdigest()

    def view_signature(self, db, schema, tablename):
        """Returns the definition of the view"""
        cur = db.cursor()
        query = """SELECT view_definition
                    FROM information_schema.views
                    WHERE table_name=%s AND table_schema=%s
                """
        cur.execute(query, (tablename, schema))
        row = cur.fetchone()
        return row[0]

    def signature(self):
        try:
            conn_string = "host=\'{}\' dbname='{}' port={} user=tuttle password=tuttle".format(self._server, self._database,
                                                                   self._port)
            db = psycopg2.connect(conn_string)
        except psycopg2.OperationalError:
            return False
        result = False
        try:
            object_type = self.pg_object_type(db, self._schema, self._objectname)
            if object_type == 'r':
                result = self.table_signature(db, self._schema, self._objectname)
            elif object_type == 'v':
                result = self.view_signature(db, self._schema, self._objectname)
        finally:
            db.close()
        return result