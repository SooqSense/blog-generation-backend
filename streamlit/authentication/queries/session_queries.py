"""
Session-related SQL queries for authentication system
"""

class SessionQueries:
    """Collection of session-related SQL queries"""
    
    # Session tracking queries (if you want to store sessions in DB)
    CREATE_SESSION = """
        INSERT INTO user_sessions (
            user_id, session_token, created_at, expires_at, is_active
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, session_token, created_at, expires_at
    """
    
    FIND_ACTIVE_SESSION = """
        SELECT id, user_id, session_token, created_at, expires_at
        FROM user_sessions
        WHERE user_id = %s AND is_active = true AND expires_at > %s
        ORDER BY created_at DESC
        LIMIT 1
    """
    
    INVALIDATE_SESSION = """
        UPDATE user_sessions
        SET is_active = false, updated_at = %s
        WHERE user_id = %s AND session_token = %s
    """
    
    INVALIDATE_ALL_USER_SESSIONS = """
        UPDATE user_sessions
        SET is_active = false, updated_at = %s
        WHERE user_id = %s
    """
    
    CLEANUP_EXPIRED_SESSIONS = """
        UPDATE user_sessions
        SET is_active = false, updated_at = %s
        WHERE expires_at < %s AND is_active = true
    """
    
    # Session statistics
    GET_SESSION_STATS = """
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active_sessions,
            COUNT(CASE WHEN created_at > %s THEN 1 END) as recent_sessions
        FROM user_sessions
    """
    
    GET_USER_SESSION_HISTORY = """
        SELECT 
            id, session_token, created_at, expires_at, is_active
        FROM user_sessions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
