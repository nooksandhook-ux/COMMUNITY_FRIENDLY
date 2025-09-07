// Quiz Analytics Frontend
function loadQuizAnalytics() {
  fetch('/nooks_club/api/quiz/analytics')
    .then(res => res.json())
    .then(data => {
      document.getElementById('quiz-analytics').innerHTML =
        `<div class='card p-3 mb-2'>
          <b>Total Attempts:</b> ${data.total_attempts}<br>
          <b>Correct Answers:</b> ${data.correct}<br>
          <b>Accuracy:</b> ${data.accuracy.toFixed(1)}%<br>
          <b>Current Correct Streak:</b> ${data.current_streak}
        </div>`;
    });
}
