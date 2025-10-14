"""
Direct database service for chat operations
Bypasses Django ORM for direct database access
"""
import psycopg2
import json
from datetime import datetime
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DirectDBChatService:
    """Direct database service for chat operations"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            # Get environment variables - NO FALLBACKS for production safety
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')
            
            # Validate all required environment variables
            if not all([db_host, db_port, db_name, db_user, db_password]):
                missing_vars = []
                if not db_host: missing_vars.append('DB_HOST')
                if not db_port: missing_vars.append('DB_PORT')
                if not db_name: missing_vars.append('DB_NAME')
                if not db_user: missing_vars.append('DB_USER')
                if not db_password: missing_vars.append('DB_PASSWORD')
                
                raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            self.connection = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password
            )
            print("✅ Direct database connection established")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.connection = None
    
    def get_user_sessions(self, user_id, limit: int = 50) -> List[Dict]:
        """Get user sessions from database"""
        if not self.connection:
            return []
        
        # Convert string user_id to integer if needed
        try:
            if isinstance(user_id, str):
                # Extract Django user ID from session state
                import streamlit as st
                django_user_id = st.session_state.get('django_user_id')
                if django_user_id:
                    user_id = django_user_id
                else:
                    print(f"Warning: Could not get Django user ID for {user_id}")
                    return []
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"Error: Invalid user_id format: {user_id}")
            return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT id, session_id, title, created_at, updated_at, is_active
                FROM chatbot_chatsession 
                WHERE user_id = %s AND is_active = true
                ORDER BY updated_at DESC
                LIMIT %s
            """, (user_id, limit))
            
            sessions = []
            rows = cursor.fetchall()
            print(f"Found {len(rows)} sessions for user {user_id}")
            
            for row in rows:
                message_count = self._get_message_count_for_session(row[0])
                print(f"Session {row[1]}: {message_count} messages")
                sessions.append({
                    'id': row[0],
                    'session_id': row[1],
                    'title': row[2],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'is_active': row[5],
                    'message_count': message_count,
                    'last_message_time': row[4]
                })
            
            cursor.close()
            return sessions
            
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []
    
    def _get_message_count_for_session(self, session_db_id: int) -> int:
        """Helper to get message count for a given session DB ID"""
        if not self.connection:
            return 0
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM chatbot_chatmessage WHERE session_id = %s
            """, (session_db_id,))
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            print(f"Error getting message count for session {session_db_id}: {e}")
            return 0
    
    def get_session_messages(self, user_id, session_id: str) -> List[Dict]:
        """Get messages for a session"""
        if not self.connection:
            return []
        
        # Convert string user_id to integer if needed
        try:
            if isinstance(user_id, str):
                import streamlit as st
                django_user_id = st.session_state.get('django_user_id')
                if django_user_id:
                    user_id = django_user_id
                else:
                    print(f"Warning: Could not get Django user ID for {user_id}")
                    return []
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"Error: Invalid user_id format: {user_id}")
            return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT cm.message_type, cm.content, cm.timestamp, cm.sources, cm.processing_info
                FROM chatbot_chatmessage cm
                JOIN chatbot_chatsession cs ON cm.session_id = cs.id
                WHERE cs.user_id = %s AND cs.session_id = %s AND cs.is_active = true
                ORDER BY cm.timestamp ASC
            """, (user_id, session_id))
            
            messages = []
            rows = cursor.fetchall()
            print(f"Found {len(rows)} messages for session {session_id} (user {user_id})")
            
            for row in rows:
                messages.append({
                    'message_type': row[0],
                    'content': row[1],
                    'timestamp': row[2].strftime('%H:%M:%S') if row[2] else '',
                    'sources': row[3] if row[3] else [],
                    'processing_info': row[4] if row[4] else {}
                })
            
            cursor.close()
            return messages
            
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg:
                print(f"❌ Database table missing: {error_msg}")
                print("💡 Run migrations on your production database: python manage.py migrate")
            else:
                print(f"Error getting session messages: {e}")
            return []
    
    def save_message(self, user_id, session_id: str, message_type: str, 
                    content: str, sources: List = None, processing_info: Dict = None) -> bool:
        """Save a message to database"""
        if not self.connection:
            return False
        
        # Convert string user_id to integer if needed
        try:
            if isinstance(user_id, str):
                import streamlit as st
                django_user_id = st.session_state.get('django_user_id')
                if django_user_id:
                    user_id = django_user_id
                else:
                    print(f"Warning: Could not get Django user ID for {user_id}")
                    return False
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"Error: Invalid user_id format: {user_id}")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Get or create session
            cursor.execute("""
                SELECT id FROM chatbot_chatsession 
                WHERE user_id = %s AND session_id = %s AND is_active = true
            """, (user_id, session_id))
            
            session_row = cursor.fetchone()
            if not session_row:
                # Create new session
                cursor.execute("""
                    INSERT INTO chatbot_chatsession (user_id, session_id, title, created_at, updated_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, session_id, f"Chat Session {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                     datetime.now(), datetime.now(), True))
                session_id_db = cursor.fetchone()[0]
                print(f"Created new session: {session_id} -> DB ID: {session_id_db}")
            else:
                session_id_db = session_row[0]
                print(f"Found existing session: {session_id} -> DB ID: {session_id_db}")
            
            # Save message
            cursor.execute("""
                INSERT INTO chatbot_chatmessage (session_id, message_type, content, timestamp, sources, processing_info)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id_db, message_type, content, datetime.now(), 
                 json.dumps(sources or []), json.dumps(processing_info or {})))
            
            print(f"Saved message: {message_type} - {content[:50]}... to session DB ID: {session_id_db}")
            
            # Update session timestamp
            cursor.execute("""
                UPDATE chatbot_chatsession 
                SET updated_at = %s 
                WHERE id = %s
            """, (datetime.now(), session_id_db))
            
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Error saving message: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def delete_session(self, user_id, session_id: str) -> bool:
        """Delete a session (soft delete)"""
        if not self.connection:
            return False
        
        # Convert string user_id to integer if needed
        try:
            if isinstance(user_id, str):
                import streamlit as st
                django_user_id = st.session_state.get('django_user_id')
                if django_user_id:
                    user_id = django_user_id
                else:
                    print(f"Warning: Could not get Django user ID for {user_id}")
                    return False
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"Error: Invalid user_id format: {user_id}")
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE chatbot_chatsession 
                SET is_active = false 
                WHERE user_id = %s AND session_id = %s
            """, (user_id, session_id))
            
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Error deleting session: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def clear_user_sessions(self, user_id) -> bool:
        """Clear all user sessions (soft delete)"""
        if not self.connection:
            return False
        
        # Convert string user_id to integer if needed
        try:
            if isinstance(user_id, str):
                import streamlit as st
                django_user_id = st.session_state.get('django_user_id')
                if django_user_id:
                    user_id = django_user_id
                else:
                    print(f"Warning: Could not get Django user ID for {user_id}")
                    return False
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"Error: Invalid user_id format: {user_id}")
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE chatbot_chatsession 
                SET is_active = false 
                WHERE user_id = %s
            """, (user_id,))
            
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Error clearing user sessions: {e}")
            if self.connection:
                self.connection.rollback()
            return False
