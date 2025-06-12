import os
import time
import psycopg2

def wait_for_db():
    """Wait for database to be available"""
    # Check for missing environment variables
    required_vars = ['POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'DB_HOST', 'DB_PORT']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        return False

    db_config = {
        'dbname': os.getenv('POSTGRES_DB'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
    }

    print("Attempting to connect to database with configuration:")
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print(f"Database: {db_config['dbname']}")
    print(f"User: {db_config['user']}")
    print("Password: [REDACTED]")

    attempt = 1
    while True:
        try:
            print(f"\nConnection attempt {attempt}...")
            conn = psycopg2.connect(**db_config)
            conn.close()
            print("Successfully connected to the database!")
            return True
        except psycopg2.OperationalError as e:
            print(f"Database unavailable (attempt {attempt}):")
            print(f"Error details: {str(e)}")
            print("Waiting 1 second before next attempt...")
            time.sleep(1)
            attempt += 1

if __name__ == '__main__':
    wait_for_db() 