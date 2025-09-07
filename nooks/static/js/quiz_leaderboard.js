// Quiz Leaderboard Frontend
function loadQuizLeaderboard() {
  fetch('/nooks_club/api/quiz/leaderboard')
    .then(res => res.json())
    .then(data => {
      const leaderboard = data.leaderboard;
      const table = document.getElementById('quiz-leaderboard-table');
      table.innerHTML = '<tr><th>Rank</th><th>User</th><th>Score</th><th>Attempts</th></tr>';
      leaderboard.forEach((entry, i) => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${i+1}</td><td>${entry.username}${entry.is_current_user ? ' (You)' : ''}</td><td>${entry.score}</td><td>${entry.attempts}</td>`;
        table.appendChild(row);
      });
    });
}
