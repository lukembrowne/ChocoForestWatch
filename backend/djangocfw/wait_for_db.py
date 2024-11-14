import os
import time
import psycopg2

def wait_for_db():
    """Wait for database to be available"""
    db_config = {
        'dbname': os.getenv('POSTGRES_DB', 'cfwdb'),
        'user': os.getenv('POSTGRES_USER', 'cfwuser'),
        'password': os.getenv('POSTGRES_PASSWORD', '1234'),
        'host': os.getenv('DB_HOST', 'db'),
        'port': os.getenv('DB_PORT', '5432'),
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