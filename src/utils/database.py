"""
Database utilities with security measures.
"""

import sqlite3
from typing import Any, Dict, List, Optional
import re
from .logger import get_logger

logger = get_logger(__name__)


class SafeQueryBuilder:
    """Builds safe SQL queries with injection prevention."""
    
    @staticmethod
    def _sanitize_value(value: Any) -> Any:
        """Sanitize input values to prevent SQL injection."""
        if isinstance(value, str):
            # Remove dangerous SQL keywords and characters
            dangerous_patterns = [
                r"';?\s*(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|EXEC|EXECUTE)",
                r"UNION\s+SELECT",
                r"--",
                r"/\*.*\*/",
                r"xp_cmdshell",
                r"sp_executesql"
            ]
            
            for pattern in dangerous_patterns:
                value = re.sub(pattern, "", value, flags=re.IGNORECASE)
            
            # Escape single quotes
            value = value.replace("'", "''")
        
        return value
    
    @staticmethod
    def build_select_query(table: str, conditions: Dict[str, Any]) -> str:
        """Build a safe SELECT query."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise ValueError("Invalid table name")
        
        query = f"SELECT * FROM {table}"
        
        if conditions:
            where_clauses = []
            for column, value in conditions.items():
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', column):
                    raise ValueError(f"Invalid column name: {column}")
                
                sanitized_value = SafeQueryBuilder._sanitize_value(value)
                where_clauses.append(f"{column} = '{sanitized_value}'")
            
            query += " WHERE " + " AND ".join(where_clauses)
        
        return query
    
    @staticmethod
    def build_insert_query(table: str, data: Dict[str, Any]) -> str:
        """Build a safe INSERT query."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise ValueError("Invalid table name")
        
        columns = []
        values = []
        
        for column, value in data.items():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', column):
                raise ValueError(f"Invalid column name: {column}")
            
            columns.append(column)
            sanitized_value = SafeQueryBuilder._sanitize_value(value)
            values.append(f"'{sanitized_value}'")
        
        columns_str = ", ".join(columns)
        values_str = ", ".join(values)
        
        return f"INSERT INTO {table} ({columns_str}) VALUES ({values_str})"


def safe_query_builder(table: str, conditions: Dict[str, Any]) -> str:
    """Build a safe SQL query (backward compatibility function)."""
    return SafeQueryBuilder.build_select_query(table, conditions)


class DatabaseManager:
    """Secure database manager with built-in protections."""
    
    def __init__(self, db_path: str = ":memory:"):
        """Initialize database connection."""
        self.db_path = db_path
        self.connection = None
    
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            logger.error("Database connection failed: %s", e)
            return False
    
    def execute_safe_query(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Execute a query safely with parameter binding."""
        if not self.connection:
            raise RuntimeError("Database not connected")
        
        try:
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        except sqlite3.Error as e:
            logger.error("Query execution failed: %s", e)
            raise
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None