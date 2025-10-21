"""
db.py
=====
Provides a Database class for connecting to and interacting with CockroachDB using psycopg2.
Now includes a method to ensure tables exist.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

logger = logging.getLogger("TrabajoBot")

load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASS")
        self.database = os.getenv("DB_NAME")
        self.port = os.getenv("DB_PORT", 26257)

        logger.info("Initializing database connection...")
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                dbname=self.database,
                port=self.port,
                sslmode='require'
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Database connection established.")
        except Exception as e:
            logger.error(f"Failed to connect to DB: {e}")
            self.conn = None
            self.cursor = None

    def execute(self, query, params=None, commit=False):
        if not self.cursor:
            logger.error("No database cursor available (connection failed).")
            return

        logger.debug(f"Executing query: {query} | params: {params}")
        self.cursor.execute(query, params or ())
        if commit:
            self.conn.commit()

    def fetchone(self):
        if not self.cursor:
            return None
        return self.cursor.fetchone()

    def fetchall(self):
        if not self.cursor:
            return []
        return self.cursor.fetchall()

    def ensure_table_exists(self, table_name: str, creation_query: str):
        """
        Ensures the specified table exists in the database.
        :param table_name: Name of the table to check.
        :param creation_query: SQL query to create the table if it doesn't exist.
        """
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        );
        """
        self.cursor.execute(check_query, (table_name,))
        exists = self.cursor.fetchone()["exists"]

        if not exists:
            logger.info(f"Table '{table_name}' does not exist. Creating...")
            self.cursor.execute(creation_query)
            self.conn.commit()
            logger.info(f"Table '{table_name}' created successfully.")
        else:
            logger.info(f"Table '{table_name}' already exists.")

    def __del__(self):
        if self.conn:
            logger.info("Closing database connection")
            self.cursor.close()
            self.conn.close()
