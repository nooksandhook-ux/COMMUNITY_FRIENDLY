// Quiz Question Review Frontend
function loadQuizReview() {
  fetch('/nooks_club/api/quiz/review')
    .then(res => res.json())
    .then(data => {
      const review = data.review;
      const reviewDiv = document.getElementById('quiz-review');
      reviewDiv.innerHTML = '';
      review.forEach((item, i) => {
        const card = document.createElement('div');
        card.className = 'card mb-2';
        card.innerHTML = `<div class='card-body'>
          <strong>Q${i+1}:</strong> ${item.question}<br>
          <span>Your answer: <b>${item.your_answer}</b> ${item.is_correct ? '✅' : '❌'}</span><br>
          <span>Correct answer: <b>${item.correct_answer}</b></span><br>
          <small class='text-muted'>Answered at: ${new Date(item.answered_at).toLocaleString()}</small>
        </div>`;
        reviewDiv.appendChild(card);
      });
    });
}
