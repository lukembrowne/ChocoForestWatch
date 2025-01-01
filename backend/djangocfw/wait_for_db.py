import os
import time
import psycopg2

def wait_for_db():
    """Wait for database to be available"""
    db_config = {
        'dbname': os.getenv('POSTGRES_DB'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
    }

    while True:
        try:
            conn = psycopg2.connect(**db_config)
            conn.close()
            break
        except psycopg2.OperationalError:
            print('Database unavailable, waiting 1 second...')
            time.sleep(1)

if __name__ == '__main__':
    wait_for_db() 