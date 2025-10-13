"""
Database operations for authentication module
Uses Django's database connection for consistency
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

class DatabaseOperations:
    """
    Database operations for authentication
    Uses Django's database connection for consistency
    """
    
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection using Django's database connection - NO FALLBACKS for production safety"""
        try:
            # Use Django's database connection instead of creating our own
            from django.db import connection
            from django.conf import settings
            
            print("🔧 Authentication using Django's database connection")
            
            # Validate Django database configuration
            db_config = settings.DATABASES['default']
            db_host = db_config.get('HOST')
            db_name = db_config.get('NAME')
            db_user = db_config.get('USER')
            db_password = db_config.get('PASSWORD')
            
            print(f"🔍 Authentication database connection attempt:")
            print(f"   Host: {db_host}")
            print(f"   Database: {db_name}")
            print(f"   User: {db_user}")
            print(f"   Password: {'***' if db_password else 'NOT SET'}")
            
            # Validate all required database parameters
            if not all([db_host, db_name, db_user, db_password]):
                missing_vars = []
                if not db_host: missing_vars.append('DB_HOST')
                if not db_name: missing_vars.append('DB_NAME')
                if not db_user: missing_vars.append('DB_USER')
                if not db_password: missing_vars.append('DB_PASSWORD')
                
                error_msg = f"Missing required database parameters: {', '.join(missing_vars)}"
                print(f"❌ {error_msg}")
                raise Exception(error_msg)
            
            # Test Django's database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result:
                    print("✅ Authentication database connection established successfully via Django")
                    # Store Django connection for later use
                    self.connection = connection
                else:
                    raise Exception("Django database connection test failed")
                
        except Exception as e:
            print(f"❌ Authentication database connection failed: {e}")
            # Check if we're in Cloud Run environment
            if os.getenv('K_SERVICE') or os.getenv('CLOUD_RUN_SERVICE'):
                print("🌐 Running in Cloud Run - database connection not available (expected)")
                print("💡 To fix: Set proper DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD in Cloud Run environment variables")
            self.connection = None
    
    def get_connection(self):
        """Get database connection"""
        return self.connection
    
    def execute_query(self, query, params=None):
        """Execute a database query using Django's connection"""
        if not self.connection:
            raise Exception("Database connection not available")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            print(f"❌ Database query error: {e}")
            raise e
    
    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Clerk user ID using Django's connection"""
        if not self.connection:
            print("❌ Database connection not available for get_user_by_clerk_id")
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, email, clerk_user_id, is_active, is_staff, is_superuser, 
                           created_at, last_login
                    FROM users 
                    WHERE clerk_user_id = %s
                """, (clerk_user_id,))
                
                result = cursor.fetchone()
                
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
        """Get user by Django user ID using Django's connection"""
        if not self.connection:
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, email, clerk_user_id, is_active, is_staff, is_superuser, 
                           created_at, last_login
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                
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
            print(f"❌ Error getting user by ID: {e}")
            return None
    
    def create_user(self, username: str, email: str, password_hash: str, 
                   clerk_user_id: str, is_active: bool = True, 
                   is_staff: bool = False, is_superuser: bool = False) -> Optional[Dict[str, Any]]:
        """Create a new user using Django's connection"""
        if not self.connection:
            print("❌ Database connection not available for create_user")
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users 
                    (username, email, password, clerk_user_id, is_active, is_staff, is_superuser, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, username, email, clerk_user_id, is_active, is_staff, is_superuser, created_at
                """, (username, email, password_hash, clerk_user_id, is_active, is_staff, is_superuser, datetime.now(), datetime.now()))
                
                result = cursor.fetchone()
                
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
            return None
    
    def update_last_login(self, user_id: int) -> bool:
        """Update user's last login timestamp using Django's connection"""
        if not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET last_login = %s 
                    WHERE id = %s
                """, (datetime.now(), user_id))
                return True
        except Exception as e:
            print(f"❌ Error updating last login: {e}")
            return False
    
    def validate_user_session(self, user_id: int, clerk_user_id: str) -> bool:
        """Validate user session using Django's connection"""
        if not self.connection:
            return False
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM users 
                    WHERE id = %s AND clerk_user_id = %s AND is_active = true
                """, (user_id, clerk_user_id))
                
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            print(f"❌ Error validating user session: {e}")
            return False
    
    def get_user_specific_data(self, table_name: str, user_id: int, 
                             columns: str = "*", additional_filters: str = "", 
                             params: Optional[List] = None) -> List:
        """Get user-specific data with automatic isolation using Django's connection"""
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
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, query_params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            print(f"❌ Error getting user-specific data: {e}")
            return []
    
    def count_user_records(self, table_name: str, user_id: int) -> int:
        """Count user records in a table using Django's connection"""
        if not self.connection:
            return 0
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"❌ Error counting user records: {e}")
            return 0
