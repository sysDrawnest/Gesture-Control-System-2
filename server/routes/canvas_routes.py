from flask import Blueprint, request, jsonify
from routes.auth_routes import token_required
import sqlite3
import base64
from datetime import datetime
import os

canvas_bp = Blueprint('canvas', __name__)

def get_db():
    """Get database connection"""
    import sqlite3
    conn = sqlite3.connect('gesture_control.db')
    conn.row_factory = sqlite3.Row
    return conn

@canvas_bp.route('/drawings/save', methods=['POST'])
@token_required
def save_drawing():
    """Save drawing to gallery"""
    data = request.get_json()
    name = data.get('name')
    image_data = data.get('image_data')
    
    if not name or not image_data:
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    
    db = get_db()
    
    # Create drawings table if not exists
    db.execute('''
        CREATE TABLE IF NOT EXISTS drawings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            image_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    db.commit()
    
    try:
        db.execute(
            'INSERT INTO drawings (user_id, name, image_data) VALUES (?, ?, ?)',
            (request.user_id, name, image_data)
        )
        db.commit()
        return jsonify({'success': True, 'message': 'Drawing saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@canvas_bp.route('/drawings/list', methods=['GET'])
@token_required
def get_drawings():
    """Get user's drawings"""
    db = get_db()
    
    drawings = db.execute(
        'SELECT id, name, image_data, created_at FROM drawings WHERE user_id = ? ORDER BY created_at DESC',
        (request.user_id,)
    ).fetchall()
    
    db.close()
    
    return jsonify({
        'success': True,
        'drawings': [dict(drawing) for drawing in drawings]
    })

@canvas_bp.route('/drawings/<int:drawing_id>', methods=['GET'])
@token_required
def get_drawing(drawing_id):
    """Get specific drawing"""
    db = get_db()
    
    drawing = db.execute(
        'SELECT id, name, image_data, created_at FROM drawings WHERE id = ? AND user_id = ?',
        (drawing_id, request.user_id)
    ).fetchone()
    
    db.close()
    
    if drawing:
        return jsonify({'success': True, 'drawing': dict(drawing)})
    return jsonify({'success': False, 'error': 'Drawing not found'}), 404

@canvas_bp.route('/drawings/<int:drawing_id>', methods=['DELETE'])
@token_required
def delete_drawing(drawing_id):
    """Delete drawing"""
    db = get_db()
    
    db.execute('DELETE FROM drawings WHERE id = ? AND user_id = ?', (drawing_id, request.user_id))
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': 'Drawing deleted'})