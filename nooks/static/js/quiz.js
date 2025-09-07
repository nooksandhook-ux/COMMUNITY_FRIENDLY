// Quiz Frontend Integration
let quizQuestions = [];
let quizIndex = 0;
let quizScore = 0;
let quizStartTime = null;
let quizTimer = null;
const QUIZ_TIME_LIMIT = 60; // seconds

function startQuiz() {
  fetch('/nooks_club/api/quiz/start', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      quizQuestions = data.questions;
      quizIndex = 0;
      quizScore = 0;
      quizStartTime = Date.now();
      showQuestion();
      startTimer();
    });
}

function showQuestion() {
  if (quizIndex >= quizQuestions.length) {
    finishQuiz();
    return;
  }
  const q = quizQuestions[quizIndex];
  document.getElementById('quiz-question').innerText = q.question;
  const optionsDiv = document.getElementById('quiz-options');
  optionsDiv.innerHTML = '';
  q.options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'btn btn-outline-primary m-2';
    btn.innerText = opt;
    btn.onclick = () => submitAnswer(q._id, opt);
    optionsDiv.appendChild(btn);
  });
}

function submitAnswer(questionId, answer) {
  fetch('/nooks_club/api/quiz/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId, answer })
  })
    .then(res => res.json())
    .then(data => {
      if (data.is_correct) quizScore++;
      quizIndex++;
      showQuestion();
    });
}

function startTimer() {
  let timeLeft = QUIZ_TIME_LIMIT;
  quizTimer = setInterval(() => {
    timeLeft--;
    document.getElementById('quiz-timer').innerText = 'Time left: ' + timeLeft + 's';
    if (timeLeft <= 0) {
      clearInterval(quizTimer);
      finishQuiz();
    }
  }, 1000);
}

function finishQuiz() {
  clearInterval(quizTimer);
  fetch('/nooks_club/api/quiz/finish', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      document.getElementById('quiz-question').innerText = 'Quiz Complete!';
      document.getElementById('quiz-options').innerHTML = 'Score: ' + data.score + (data.completed ? ' (in time)' : ' (time up)');
      document.getElementById('quiz-timer').innerText = '';
    });
}

// To start quiz, call startQuiz() on button click or page load
