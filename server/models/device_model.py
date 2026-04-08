from utils.db import get_db
from datetime import datetime

class DeviceModel:
    
    @staticmethod
    def register_device(user_id, device_name, device_type='laptop', ip_address=None):
        """Register a new device for the user"""
        db = get_db()
        
        # Check if device name already exists for this user
        existing = db.execute(
            'SELECT id FROM devices WHERE user_id = ? AND device_name = ?',
            (user_id, device_name)
        ).fetchone()
        
        if existing:
            return None, "Device name already exists"
        
        try:
            cursor = db.execute(
                '''INSERT INTO devices (user_id, device_name, device_type, ip_address, status, last_seen) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, device_name, device_type, ip_address, 'online', datetime.now())
            )
            db.commit()
            return cursor.lastrowid, "Device registered successfully"
        except Exception as e:
            return None, f"Error registering device: {str(e)}"
    
    @staticmethod
    def get_user_devices(user_id):
        """Get all devices for a user"""
        db = get_db()
        devices = db.execute(
            '''SELECT id, device_name, device_type, ip_address, status, 
                      last_seen, created_at 
               FROM devices WHERE user_id = ? ORDER BY created_at DESC''',
            (user_id,)
        ).fetchall()
        
        return [dict(device) for device in devices]
    
    @staticmethod
    def get_device(device_id, user_id):
        """Get specific device details"""
        db = get_db()
        device = db.execute(
            'SELECT * FROM devices WHERE id = ? AND user_id = ?',
            (device_id, user_id)
        ).fetchone()
        
        return dict(device) if device else None
    
    @staticmethod
    def update_device_status(device_id, user_id, status):
        """Update device online/offline status"""
        db = get_db()
        db.execute(
            'UPDATE devices SET status = ?, last_seen = ? WHERE id = ? AND user_id = ?',
            (status, datetime.now(), device_id, user_id)
        )
        db.commit()
        return True
    
    @staticmethod
    def delete_device(device_id, user_id):
        """Delete a device"""
        db = get_db()
        db.execute('DELETE FROM devices WHERE id = ? AND user_id = ?', (device_id, user_id))
        db.commit()
        return True
    
    @staticmethod
    def log_gesture(user_id, device_id, gesture_type, confidence, response_time):
        """Log gesture for analytics"""
        db = get_db()
        db.execute(
            '''INSERT INTO gesture_logs (user_id, device_id, gesture_type, confidence, response_time) 
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, device_id, gesture_type, confidence, response_time)
        )
        db.commit()
        return True
    
    @staticmethod
    def get_gesture_stats(user_id, device_id=None, days=7):
        """Get gesture statistics for analytics"""
        db = get_db()
        
        query = '''
            SELECT 
                gesture_type,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence,
                AVG(response_time) as avg_response_time
            FROM gesture_logs
            WHERE user_id = ? AND timestamp > datetime('now', ?)
        '''
        
        params = [user_id, f'-{days} days']
        
        if device_id:
            query += ' AND device_id = ?'
            params.append(device_id)
        
        query += ' GROUP BY gesture_type'
        
        stats = db.execute(query, params).fetchall()
        return [dict(stat) for stat in stats]