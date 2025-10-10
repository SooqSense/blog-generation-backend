"""
Database operations for authentication module
"""
import psycopg2
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseOperations:
    """
    Database operations for authentication
    """
    
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'ai_blog_generation'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
        except Exception as e:
            print(f"❌ Authentication database connection failed: {e}")
            self.connection = None
    
    def get_connection(self):
        """Get database connection"""
        return self.connection
    
    def execute_query(self, query, params=None):
        """Execute a database query"""
        if not self.connection:
            raise Exception("Database connection not available")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            print(f"❌ Database query error: {e}")
            raise e
    
    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Clerk user ID"""
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT id, username, email, clerk_user_id, is_active, is_staff, is_superuser, 
                       created_at, last_login
                FROM users 
                WHERE clerk_user_id = %s
            """, (clerk_user_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'django_user_id': result[0],
                    'username': result[1],
                    'email': result[2],
                    'clerk_user_id': result[3],
                    'is_active': result[4],
                    'is_staff': result[5],
                    'is_superuser': result[6],
                    'date_joined': result[7],
                    'last_login': result[8]
                }
            return None
        except Exception as e:
            print(f"❌ Error getting user by Clerk ID: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Django user ID"""
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT id, username, email, clerk_user_id, is_active, is_staff, is_superuser, 
                       created_at, last_login
                FROM users 
                WHERE id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'id': result[0],
                    'django_user_id': result[0],
                    'username': result[1],
                    'email': result[2],
                    'clerk_user_id': result[3],
                    'is_active': result[4],
                    'is_staff': result[5],
                    'is_superuser': result[6],
                    'date_joined': result[7],
                    'last_login': result[8]
                }
            return None
        except Exception as e:
            print(f"❌ Error getting user by ID: {e}")
            return None
    
    def create_user(self, username: str, email: str, password_hash: str, 
                   clerk_user_id: str, is_active: bool = True, 
                   is_staff: bool = False, is_superuser: bool = False) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO users 
                (username, email, password, clerk_user_id, is_active, is_staff, is_superuser, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, username, email, clerk_user_id, is_active, is_staff, is_superuser, created_at
            """, (username, email, password_hash, clerk_user_id, is_active, is_staff, is_superuser, datetime.now(), datetime.now()))
            
            result = cursor.fetchone()
            self.connection.commit()
            cursor.close()
            
            if result:
                return {
                    'django_user_id': result[0],
                    'username': result[1],
                    'email': result[2],
                    'clerk_user_id': result[3],
                    'is_active': result[4],
                    'is_staff': result[5],
                    'is_superuser': result[6],
                    'date_joined': result[7],
                    'last_login': None
                }
            return None
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            self.connection.rollback()
            return None
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE users 
                SET last_login = %s 
                WHERE id = %s
            """, (datetime.now(), user_id))
            
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"❌ Error updating last login: {e}")
            self.connection.rollback()
            return False
    
    def validate_user_session(self, user_id: int, clerk_user_id: str) -> bool:
        """Validate user session"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT id FROM users 
                WHERE id = %s AND clerk_user_id = %s AND is_active = true
            """, (user_id, clerk_user_id))
            
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            print(f"❌ Error validating user session: {e}")
            return False
    
    def get_user_specific_data(self, table_name: str, user_id: int, 
                             columns: str = "*", additional_filters: str = "", 
                             params: Optional[List] = None) -> List:
        """Get user-specific data with automatic isolation"""
        if not self.connection:
            return []
        
        try:
            # Build the query with user isolation
            query = f"SELECT {columns} FROM {table_name} WHERE user_id = %s"
            query_params = [user_id]
            
            if additional_filters:
                query += f" AND {additional_filters}"
                if params:
                    query_params.extend(params)
            
            cursor = self.connection.cursor()
            cursor.execute(query, query_params)
            result = cursor.fetchall()
            cursor.close()
            
            return result
        except Exception as e:
            print(f"❌ Error getting user-specific data: {e}")
            return []
    
    def count_user_records(self, table_name: str, user_id: int) -> int:
        """Count user records in a table"""
        if not self.connection:
            return 0
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            cursor.close()
            
            return result[0] if result else 0
        except Exception as e:
            print(f"❌ Error counting user records: {e}")
            return 0
