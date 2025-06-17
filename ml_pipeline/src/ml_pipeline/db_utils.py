"""
ml_pipeline.db_utils
~~~~~~~~~~~~~~~~~~~
Utility functions for interacting with PostgreSQL database.

Requires
--------
pip install sqlalchemy python-dotenv psycopg2-binary
"""

from __future__ import annotations
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

def get_db_connection(
    host: str = "localhost",
    port: Optional[str] = None,
    db_name: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None
) -> Engine:
    """
    Get a SQLAlchemy engine configured for PostgreSQL database.
    
    Parameters
    ----------
    host : str, optional
        Database host. Can be "localhost" for local database or "remote" to use DB_IP from environment variables, by default "localhost"
    port : str, optional
        Database port. If None, uses DB_PORT from environment
    db_name : str, optional
        Database name. If None, uses POSTGRES_DB from environment
    user : str, optional
        Database user. If None, uses POSTGRES_USER from environment
    password : str, optional
        Database password. If None, uses POSTGRES_PASSWORD from environment
        
    Returns
    -------
    Engine
        SQLAlchemy engine instance
    """
    print("Getting DB connection...")
    print("Loading environment variables...")
    load_dotenv()
    
    # Use provided values or fall back to environment variables
    if(host == "remote"):
        host_ip = os.getenv('DB_IP')
        if host_ip is None:
            raise ValueError("DB_IP environment variable is not set")
    else:
        host_ip = "localhost"
        
    port = port or os.getenv('DB_PORT')
    db_name = db_name or os.getenv('POSTGRES_DB')
    user = user or os.getenv('POSTGRES_USER')
    password = password or os.getenv('POSTGRES_PASSWORD')
    
    # Create database connection URL
    print("Creating database connection URL...")
    db_url = f"postgresql://{user}:{password}@{host_ip}:{port}/{db_name}"
    
    # Create and return engine
    print("Creating engine...")
    return create_engine(db_url)
