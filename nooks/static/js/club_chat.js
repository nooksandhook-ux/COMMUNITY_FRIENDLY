// Club Chat Frontend Integration (Socket.IO)
const socket = io();
const clubId = document.getElementById('club-chat-box')?.dataset.clubId;
const chatBox = document.getElementById('chat-box');
const chatInput = document.getElementById('chat-input');
const chatForm = document.getElementById('chat-form');

if (clubId) {
  socket.emit('join_club', { club_id: clubId });

  socket.on('receive_message', function(data) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message';
    msgDiv.innerText = data.user_id + ': ' + data.message;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  });

  chatForm?.addEventListener('submit', function(e) {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (message) {
      socket.emit('send_message', { club_id: clubId, message });
      chatInput.value = '';
    }
  });
}
