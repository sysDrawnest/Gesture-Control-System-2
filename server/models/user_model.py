from utils.db import get_db
import bcrypt
import jwt
from datetime import datetime, timedelta
from config import Config
import re

class UserModel:
    
    @staticmethod
    def create_user(username, email, password):
        """Create a new user"""
        # Validate input
        if not username or not email or not password:
            return None, "All fields are required"
        
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return None, "Username must be 3-20 characters (letters, numbers, underscore)"
        
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return None, "Invalid email format"
        
        if len(password) < 6:
            return None, "Password must be at least 6 characters"
        
        db = get_db()
        
        # Check if user exists
        existing = db.execute('SELECT id FROM users WHERE username = ? OR email = ?', 
                             (username, email)).fetchone()
        if existing:
            return None, "Username or email already exists"
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Insert user
        try:
            cursor = db.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            db.commit()
            return cursor.lastrowid, "User created successfully"
        except Exception as e:
            return None, f"Database error: {str(e)}"
    
    @staticmethod
    def authenticate_user(username, password):
        """Authenticate user and return JWT token"""
        db = get_db()
        
        user = db.execute(
            'SELECT id, username, email, password_hash FROM users WHERE username = ? AND is_active = 1',
            (username,)
        ).fetchone()
        
        if not user:
            return None, "Invalid username or password"
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return None, "Invalid username or password"
        
        # Update last login
        db.execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
            (user['id'],)
        )
        db.commit()
        
        # Generate JWT token
        token = jwt.encode(
            {
                'user_id': user['id'],
                'username': user['username'],
                'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
            },
            Config.JWT_SECRET,
            algorithm='HS256'
        )
        
        # Store session
        expires_at = datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
        db.execute(
            'INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)',
            (user['id'], token, expires_at)
        )
        db.commit()
        
        return {
            'token': token,
            'user_id': user['id'],
            'username': user['username'],
            'email': user['email']
        }, "Authentication successful"
    
    @staticmethod
    def verify_token(token):
        """Verify JWT token"""
        try:
            # Use import inside to avoid circular deps if any
            from config import Config
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            
            # Check if token is revoked
            db = get_db()
            session = db.execute(
                'SELECT is_revoked FROM sessions WHERE token = ?',
                (token,)
            ).fetchone()
            
            if not session:
                return None, "Token not found in session store"
                
            if session['is_revoked']:
                return None, "Token revoked"
            
            return payload, "Valid token"
        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
        except Exception as e:
            return None, f"Token verification error: {str(e)}"
    
    @staticmethod
    def logout_user(token):
        """Revoke user token"""
        db = get_db()
        db.execute('UPDATE sessions SET is_revoked = 1 WHERE token = ?', (token,))
        db.commit()
        return True, "Logged out successfully"
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user information by ID"""
        db = get_db()
        user = db.execute(
            'SELECT id, username, email, created_at, last_login FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        
        if user:
            return dict(user), None
        return None, "User not found"
    
    @staticmethod
    def update_user_profile(user_id, email=None, password=None):
        """Update user profile"""
        db = get_db()
        
        if email:
            db.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
        
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        
        db.commit()
        return True, "Profile updated successfully"