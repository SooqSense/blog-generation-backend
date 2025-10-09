"""
User-related SQL queries for authentication system
"""

class UserQueries:
    """Collection of user-related SQL queries"""
    
    # User lookup queries
    FIND_USER_BY_CLERK_ID = """
        SELECT id, username, email, clerk_user_id, created_at, updated_at, last_login, is_active
        FROM users 
        WHERE clerk_user_id = %s
    """
    
    FIND_USER_BY_ID = """
        SELECT id, username, email, clerk_user_id, created_at, updated_at, last_login, is_active
        FROM users 
        WHERE id = %s
    """
    
    FIND_USER_BY_EMAIL = """
        SELECT id, username, email, clerk_user_id, created_at, updated_at, last_login, is_active
        FROM users 
        WHERE email = %s
    """
    
    # User creation queries
    CREATE_USER = """
        INSERT INTO users (
            username, email, password, clerk_user_id, is_active, is_staff, is_superuser,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, username, email, clerk_user_id, created_at, updated_at
    """
    
    # User update queries
    UPDATE_LAST_LOGIN = """
        UPDATE users 
        SET last_login = %s, updated_at = %s
        WHERE id = %s
    """
    
    UPDATE_USER_INFO = """
        UPDATE users 
        SET username = %s, email = %s, updated_at = %s
        WHERE id = %s
    """
    
    DEACTIVATE_USER = """
        UPDATE users 
        SET is_active = %s, updated_at = %s
        WHERE id = %s
    """
    
    # User validation queries
    VALIDATE_USER_SESSION = """
        SELECT id, is_active, clerk_user_id
        FROM users 
        WHERE id = %s AND clerk_user_id = %s
    """
    
    CHECK_USER_EXISTS = """
        SELECT COUNT(*) as count
        FROM users 
        WHERE clerk_user_id = %s
    """
    
    # User data isolation queries
    GET_USER_SPECIFIC_DATA = """
        SELECT {columns}
        FROM {table_name}
        WHERE user_id = %s
    """
    
    COUNT_USER_RECORDS = """
        SELECT COUNT(*) as count
        FROM {table_name}
        WHERE user_id = %s
    """
    
    # User statistics queries
    GET_USER_STATS = """
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
            COUNT(CASE WHEN last_login > %s THEN 1 END) as recent_logins
        FROM users
    """
    
    GET_USER_ACTIVITY = """
        SELECT 
            id, username, email, last_login, created_at
        FROM users 
        WHERE id = %s
    """
