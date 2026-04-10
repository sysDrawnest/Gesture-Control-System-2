from utils.db import get_db
from datetime import datetime
import logging

# Setup logging
logger = logging.getLogger(__name__)

class DeviceModel:
    
    @staticmethod
    def register_device(user_id, device_name, device_type='laptop', ip_address=None):
        """Register a new device for the user"""
        db = get_db()
        
        # Validate inputs
        if not user_id:
            logger.error("Cannot register device: user_id is required")
            return None, "User ID is required"
        
        if not device_name:
            device_name = f"Device_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Generated device name: {device_name}")
        
        try:
            # Check if device name already exists for this user
            existing = db.execute(
                'SELECT id FROM devices WHERE user_id = ? AND device_name = ?',
                (user_id, device_name)
            ).fetchone()
            
            if existing:
                logger.info(f"Device '{device_name}' already exists for user {user_id}. Returning existing ID.")
                return existing['id'], "Device already registered"
            
            # Insert new device
            cursor = db.execute(
                '''INSERT INTO devices (user_id, device_name, device_type, ip_address, status, last_seen) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, device_name, device_type, ip_address, 'online', datetime.now())
            )
            db.commit()
            
            device_id = cursor.lastrowid
            logger.info(f"Device registered successfully: ID={device_id}, Name={device_name}, User={user_id}")
            return device_id, "Device registered successfully"
            
        except Exception as e:
            logger.error(f"Error registering device: {str(e)}")
            return None, f"Error registering device: {str(e)}"
    
    @staticmethod
    def get_user_devices(user_id):
        """Get all devices for a user"""
        db = get_db()
        
        try:
            devices = db.execute(
                '''SELECT id, device_name, device_type, ip_address, status, 
                          last_seen, created_at 
                   FROM devices 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC''',
                (user_id,)
            ).fetchall()
            
            logger.info(f"Retrieved {len(devices)} devices for user {user_id}")
            return [dict(device) for device in devices]
            
        except Exception as e:
            logger.error(f"Error getting devices for user {user_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_device(device_id, user_id):
        """Get specific device details"""
        db = get_db()
        
        try:
            device = db.execute(
                'SELECT * FROM devices WHERE id = ? AND user_id = ?',
                (device_id, user_id)
            ).fetchone()
            
            if device:
                logger.debug(f"Device found: ID={device_id}")
                return dict(device)
            else:
                logger.warning(f"Device not found: ID={device_id}, User={user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting device {device_id}: {str(e)}")
            return None
    
    @staticmethod
    def update_device_status(device_id, user_id, status):
        """Update device online/offline status"""
        db = get_db()
        
        try:
            db.execute(
                'UPDATE devices SET status = ?, last_seen = ? WHERE id = ? AND user_id = ?',
                (status, datetime.now(), device_id, user_id)
            )
            db.commit()
            logger.info(f"Device {device_id} status updated to '{status}'")
            return True
            
        except Exception as e:
            logger.error(f"Error updating device {device_id} status: {str(e)}")
            return False
    
    @staticmethod
    def delete_device(device_id, user_id):
        """Delete a device"""
        db = get_db()
        
        try:
            # First check if device exists
            device = db.execute(
                'SELECT id FROM devices WHERE id = ? AND user_id = ?',
                (device_id, user_id)
            ).fetchone()
            
            if not device:
                logger.warning(f"Cannot delete: Device {device_id} not found for user {user_id}")
                return False
            
            # Delete the device
            db.execute('DELETE FROM devices WHERE id = ? AND user_id = ?', (device_id, user_id))
            db.commit()
            logger.info(f"Device {device_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting device {device_id}: {str(e)}")
            return False
    
    @staticmethod
    def log_gesture(user_id, device_id, gesture_type, confidence, response_time):
        """Log gesture for analytics"""
        db = get_db()
        
        # Validate required fields
        if not user_id:
            logger.error("Cannot log gesture: user_id is None")
            return False
        
        if not device_id:
            logger.error(f"Cannot log gesture: device_id is None for user {user_id}")
            return False
        
        if not gesture_type:
            logger.error(f"Cannot log gesture: gesture_type is required")
            return False
        
        try:
            # Check if device exists before logging
            device_check = db.execute(
                'SELECT id FROM devices WHERE id = ? AND user_id = ?',
                (device_id, user_id)
            ).fetchone()
            
            if not device_check:
                logger.error(f"Cannot log gesture: Device {device_id} not found for user {user_id}")
                return False
            
            # Insert gesture log
            db.execute(
                '''INSERT INTO gesture_logs (user_id, device_id, gesture_type, confidence, response_time, timestamp) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, device_id, gesture_type, confidence, response_time, datetime.now())
            )
            db.commit()
            
            logger.debug(f"Gesture logged: user={user_id}, device={device_id}, type={gesture_type}, confidence={confidence}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging gesture: {str(e)}")
            return False
    
    @staticmethod
    def get_gesture_stats(user_id, device_id=None, days=7):
        """Get gesture statistics for analytics"""
        db = get_db()
        
        try:
            # Build query with proper date filtering
            query = '''
                SELECT 
                    gesture_type,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence,
                    AVG(response_time) as avg_response_time,
                    MIN(timestamp) as first_occurrence,
                    MAX(timestamp) as last_occurrence
                FROM gesture_logs
                WHERE user_id = ? 
                AND timestamp >= datetime('now', ?)
            '''
            
            params = [user_id, f'-{days} days']
            
            if device_id:
                query += ' AND device_id = ?'
                params.append(device_id)
            
            query += ' GROUP BY gesture_type ORDER BY count DESC'
            
            stats = db.execute(query, params).fetchall()
            
            result = []
            for stat in stats:
                result.append({
                    'gesture_type': stat['gesture_type'],
                    'count': stat['count'],
                    'avg_confidence': round(stat['avg_confidence'], 3) if stat['avg_confidence'] else 0,
                    'avg_response_time': round(stat['avg_response_time'], 4) if stat['avg_response_time'] else 0,
                    'first_seen': stat['first_occurrence'],
                    'last_seen': stat['last_occurrence']
                })
            
            logger.info(f"Retrieved gesture stats for user {user_id}: {len(result)} gesture types")
            return result
            
        except Exception as e:
            logger.error(f"Error getting gesture stats: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_gestures(user_id, device_id=None, limit=50):
        """Get recent gestures for real-time display"""
        db = get_db()
        
        try:
            query = '''
                SELECT id, device_id, gesture_type, confidence, response_time, timestamp
                FROM gesture_logs
                WHERE user_id = ?
            '''
            
            params = [user_id]
            
            if device_id:
                query += ' AND device_id = ?'
                params.append(device_id)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            gestures = db.execute(query, params).fetchall()
            
            return [dict(gesture) for gesture in gestures]
            
        except Exception as e:
            logger.error(f"Error getting recent gestures: {str(e)}")
            return []
    
    @staticmethod
    def get_device_activity_summary(user_id, device_id=None):
        """Get summary of device activity"""
        db = get_db()
        
        try:
            query = '''
                SELECT 
                    COUNT(DISTINCT DATE(timestamp)) as active_days,
                    COUNT(*) as total_gestures,
                    AVG(confidence) as avg_confidence,
                    MAX(timestamp) as last_activity
                FROM gesture_logs
                WHERE user_id = ?
            '''
            
            params = [user_id]
            
            if device_id:
                query += ' AND device_id = ?'
                params.append(device_id)
            
            summary = db.execute(query, params).fetchone()
            
            if summary:
                return {
                    'active_days': summary['active_days'] or 0,
                    'total_gestures': summary['total_gestures'] or 0,
                    'avg_confidence': round(summary['avg_confidence'], 3) if summary['avg_confidence'] else 0,
                    'last_activity': summary['last_activity']
                }
            return {
                'active_days': 0,
                'total_gestures': 0,
                'avg_confidence': 0,
                'last_activity': None
            }
            
        except Exception as e:
            logger.error(f"Error getting device activity summary: {str(e)}")
            return {
                'active_days': 0,
                'total_gestures': 0,
                'avg_confidence': 0,
                'last_activity': None
            }
    
    @staticmethod
    def clear_old_gestures(user_id, days=30):
        """Clear gestures older than specified days"""
        db = get_db()
        
        try:
            db.execute(
                'DELETE FROM gesture_logs WHERE user_id = ? AND timestamp < datetime("now", ?)',
                (user_id, f'-{days} days')
            )
            db.commit()
            logger.info(f"Cleared gestures older than {days} days for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing old gestures: {str(e)}")
            return False