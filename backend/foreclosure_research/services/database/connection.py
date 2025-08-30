"""
Database Connection Manager for 4-Plex Foreclosure Research System
Handles PostgreSQL, Neo4j, and Redis connections
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from neo4j import GraphDatabase
import redis
from redis.sentinel import Sentinel

from .models import Base
from config.settings import Settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Centralized database connection manager"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._postgres_engine = None
        self._session_factory = None
        self._neo4j_driver = None
        self._redis_client = None
        
    def initialize(self):
        """Initialize all database connections"""
        self._setup_postgres()
        self._setup_neo4j()
        self._setup_redis()
        
    def _setup_postgres(self):
        """Setup PostgreSQL connection"""
        try:
            # Create engine with connection pooling
            self._postgres_engine = create_engine(
                self.settings.DATABASE_URL,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=self.settings.DEBUG
            )
            
            # Create session factory
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._postgres_engine
            )
            
            # Add connection event listeners for monitoring
            @event.listens_for(self._postgres_engine, "connect")
            def receive_connect(dbapi_connection, connection_record):
                logger.debug("PostgreSQL connection established")
                
            @event.listens_for(self._postgres_engine, "checkout")
            def receive_checkout(dbapi_connection, connection_record, connection_proxy):
                logger.debug("PostgreSQL connection checked out")
                
            # Create tables if they don't exist
            Base.metadata.create_all(bind=self._postgres_engine)
            
            logger.info("PostgreSQL connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise
            
    def _setup_neo4j(self):
        """Setup Neo4j connection"""
        try:
            self._neo4j_driver = GraphDatabase.driver(
                self.settings.NEO4J_URL,
                auth=(self.settings.NEO4J_USERNAME, self.settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
            
            # Verify connectivity
            with self._neo4j_driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                if test_value != 1:
                    raise Exception("Neo4j connectivity test failed")
                    
            # Create constraints and indexes
            self._setup_neo4j_schema()
            
            logger.info("Neo4j connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j: {e}")
            raise
            
    def _setup_neo4j_schema(self):
        """Setup Neo4j schema constraints and indexes"""
        with self._neo4j_driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT property_id IF NOT EXISTS FOR (p:Property) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT parcel_number IF NOT EXISTS FOR (p:Property) REQUIRE p.parcel_number IS UNIQUE",
                "CREATE CONSTRAINT county_name IF NOT EXISTS FOR (c:County) REQUIRE c.name IS UNIQUE",
                "CREATE CONSTRAINT owner_id IF NOT EXISTS FOR (o:Owner) REQUIRE o.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.warning(f"Constraint creation warning: {e}")
                    
            # Create indexes
            indexes = [
                "CREATE INDEX property_address IF NOT EXISTS FOR (p:Property) ON (p.address)",
                "CREATE INDEX property_status IF NOT EXISTS FOR (p:Property) ON (p.status)",
                "CREATE INDEX foreclosure_stage IF NOT EXISTS FOR (f:Foreclosure) ON (f.stage)",
                "CREATE INDEX sale_date IF NOT EXISTS FOR (f:Foreclosure) ON (f.sale_date)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
                    
    def _setup_redis(self):
        """Setup Redis connection"""
        try:
            # Parse Redis URL
            redis_url = self.settings.REDIS_URL
            
            if redis_url.startswith('redis://'):
                self._redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            else:
                # Fallback to basic connection
                self._redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                
            # Test connection
            self._redis_client.ping()
            
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
            
    @contextmanager
    def get_postgres_session(self) -> Generator[Session, None, None]:
        """Get PostgreSQL session context manager"""
        if not self._session_factory:
            raise RuntimeError("PostgreSQL not initialized")
            
        session = self._session_factory()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
            
    @contextmanager
    def get_neo4j_session(self):
        """Get Neo4j session context manager"""
        if not self._neo4j_driver:
            raise RuntimeError("Neo4j not initialized")
            
        session = self._neo4j_driver.session()
        try:
            yield session
        except Exception as e:
            logger.error(f"Neo4j session error: {e}")
            raise
        finally:
            session.close()
            
    def get_redis_client(self) -> redis.Redis:
        """Get Redis client"""
        if not self._redis_client:
            raise RuntimeError("Redis not initialized")
        return self._redis_client
        
    def close_all(self):
        """Close all database connections"""
        if self._postgres_engine:
            self._postgres_engine.dispose()
            
        if self._neo4j_driver:
            self._neo4j_driver.close()
            
        if self._redis_client:
            self._redis_client.close()
            
        logger.info("All database connections closed")


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def initialize_databases(settings: Settings):
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager(settings)
    db_manager.initialize()


def get_db_session() -> Generator[Session, None, None]:
    """Get PostgreSQL session - convenience function"""
    if not db_manager:
        raise RuntimeError("Database not initialized")
    
    with db_manager.get_postgres_session() as session:
        yield session


def get_neo4j_session():
    """Get Neo4j session - convenience function"""
    if not db_manager:
        raise RuntimeError("Database not initialized")
        
    with db_manager.get_neo4j_session() as session:
        yield session


def get_redis_client() -> redis.Redis:
    """Get Redis client - convenience function"""
    if not db_manager:
        raise RuntimeError("Database not initialized")
    return db_manager.get_redis_client()


class Neo4jPropertyGraph:
    """Neo4j graph operations for property relationships"""
    
    def __init__(self):
        if not db_manager:
            raise RuntimeError("Database not initialized")
        self.driver = db_manager._neo4j_driver
        
    def create_property_node(self, property_data: dict):
        """Create property node in Neo4j"""
        with self.driver.session() as session:
            query = """
            MERGE (p:Property {id: $id})
            SET p.address = $address,
                p.county = $county,
                p.parcel_number = $parcel_number,
                p.status = $status,
                p.units = $units,
                p.is_4plex = $is_4plex,
                p.updated_at = datetime()
            RETURN p
            """
            
            result = session.run(query, property_data)
            return result.single()
            
    def create_county_relationship(self, property_id: int, county: str):
        """Create relationship between property and county"""
        with self.driver.session() as session:
            query = """
            MATCH (p:Property {id: $property_id})
            MERGE (c:County {name: $county})
            MERGE (p)-[:LOCATED_IN]->(c)
            """
            
            session.run(query, {"property_id": property_id, "county": county})
            
    def create_owner_relationship(self, property_id: int, owner_data: dict):
        """Create relationship between property and owner"""
        with self.driver.session() as session:
            query = """
            MATCH (p:Property {id: $property_id})
            MERGE (o:Owner {name: $owner_name})
            SET o.address = $owner_address,
                o.phone = $owner_phone,
                o.email = $owner_email
            MERGE (o)-[:OWNS]->(p)
            """
            
            params = {"property_id": property_id}
            params.update(owner_data)
            session.run(query, params)
            
    def find_similar_properties(self, property_id: int, limit: int = 10):
        """Find similar properties based on characteristics"""
        with self.driver.session() as session:
            query = """
            MATCH (p1:Property {id: $property_id})
            MATCH (p2:Property)
            WHERE p1 <> p2
              AND p2.county = p1.county
              AND p2.units = p1.units
              AND p2.is_4plex = true
            RETURN p2
            ORDER BY abs(p2.square_footage - p1.square_footage)
            LIMIT $limit
            """
            
            result = session.run(query, {"property_id": property_id, "limit": limit})
            return [record["p2"] for record in result]
            
    def get_county_statistics(self, county: str):
        """Get statistics for properties in a county"""
        with self.driver.session() as session:
            query = """
            MATCH (p:Property)-[:LOCATED_IN]->(c:County {name: $county})
            WHERE p.is_4plex = true
            RETURN 
                count(p) as total_properties,
                count(CASE WHEN p.status = 'foreclosure' THEN 1 END) as foreclosure_count,
                count(CASE WHEN p.status = 'tax_lien' THEN 1 END) as tax_lien_count,
                avg(p.assessed_value) as avg_value,
                avg(p.investment_score) as avg_score
            """
            
            result = session.run(query, {"county": county})
            return result.single()


# Connection health check functions
def check_postgres_health() -> bool:
    """Check PostgreSQL connection health"""
    try:
        with get_db_session() as session:
            result = session.execute("SELECT 1")
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False


def check_neo4j_health() -> bool:
    """Check Neo4j connection health"""
    try:
        with get_neo4j_session() as session:
            result = session.run("RETURN 1 as test")
            return result.single()["test"] == 1
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return False


def check_redis_health() -> bool:
    """Check Redis connection health"""
    try:
        redis_client = get_redis_client()
        return redis_client.ping()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


def get_database_health():
    """Get overall database health status"""
    return {
        "postgres": check_postgres_health(),
        "neo4j": check_neo4j_health(), 
        "redis": check_redis_health(),
        "timestamp": datetime.utcnow().isoformat()
    }