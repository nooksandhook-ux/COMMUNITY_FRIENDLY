from flask import Flask, session, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_login import current_user
from models import ClubChatMessageModel
import os

from app import app  # Use the main app instance

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('join_club')
def handle_join_club(data):
    club_id = data.get('club_id')
    user_id = str(current_user.id) if hasattr(current_user, 'id') else None
    join_room(club_id)
    emit('status', {'msg': f'User {user_id} has joined the club.'}, room=club_id)

@socketio.on('leave_club')
def handle_leave_club(data):
    club_id = data.get('club_id')
    user_id = str(current_user.id) if hasattr(current_user, 'id') else None
    leave_room(club_id)
    emit('status', {'msg': f'User {user_id} has left the club.'}, room=club_id)

@socketio.on('send_message')
def handle_send_message(data):
    club_id = data.get('club_id')
    message = data.get('message')
    user_id = str(current_user.id) if hasattr(current_user, 'id') else None
    # Save to DB
    if club_id and user_id and message:
        ClubChatMessageModel.send_message(club_id, user_id, message)
        emit('receive_message', {'user_id': user_id, 'message': message}, room=club_id)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
