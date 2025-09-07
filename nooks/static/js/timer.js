// Timer functionality for Hook

class Timer {
    constructor() {
        this.duration = 25 * 60; // 25 minutes in seconds
        this.timeLeft = this.duration;
        this.isRunning = false;
        this.isPaused = false;
        this.interval = null;
        this.taskName = '';
        this.timerType = 'work';
        this.category = 'general';
        
        this.initializeElements();
        this.bindEvents();
        this.checkActiveTimer();
    }
    
    initializeElements() {
        this.minutesDisplay = document.getElementById('minutes');
        this.secondsDisplay = document.getElementById('seconds');
        this.taskNameDisplay = document.getElementById('task-name');
        this.timerTypeDisplay = document.getElementById('timer-type');
        this.progressBar = document.getElementById('progress-bar');
        
        this.startBtn = document.getElementById('start-btn');
        this.pauseBtn = document.getElementById('pause-btn');
        this.stopBtn = document.getElementById('stop-btn');
        this.resetBtn = document.getElementById('reset-btn');
        
        this.taskNameInput = document.getElementById('task_name');
        this.durationInput = document.getElementById('duration');
        this.timerTypeInput = document.getElementById('timer_type');
        this.categoryInput = document.getElementById('category');
    }
    
    bindEvents() {
        this.startBtn.addEventListener('click', () => this.start());
        this.pauseBtn.addEventListener('click', () => this.pause());
        this.stopBtn.addEventListener('click', () => this.stop());
        this.resetBtn.addEventListener('click', () => this.reset());
        
        // Preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const duration = parseInt(e.target.dataset.duration);
                const type = e.target.dataset.type;
                this.setPreset(duration, type);
            });
        });
        
        // Duration input change
        this.durationInput.addEventListener('change', () => {
            if (!this.isRunning) {
                this.duration = parseInt(this.durationInput.value) * 60;
                this.timeLeft = this.duration;
                this.updateDisplay();
            }
        });
        
        // Complete session button
        document.getElementById('complete-session').addEventListener('click', () => {
            this.completeSession();
        });
    }
    
    setPreset(duration, type) {
        this.durationInput.value = duration;
        this.timerTypeInput.value = type;
        
        if (!this.isRunning) {
            this.duration = duration * 60;
            this.timeLeft = this.duration;
            this.timerType = type;
            this.updateDisplay();
            this.updateTimerInfo();
        }
    }
    
    start() {
        if (!this.taskNameInput.value.trim()) {
            showToast('Please enter a task name', 'warning');
            this.taskNameInput.focus();
            return;
        }
        
        if (!this.isRunning) {
            this.taskName = this.taskNameInput.value.trim();
            this.duration = parseInt(this.durationInput.value) * 60;
            this.timerType = this.timerTypeInput.value;
            this.category = this.categoryInput.value;
            
            if (this.timeLeft === this.duration || this.timeLeft === 0) {
                this.timeLeft = this.duration;
            }
            
            // Send start request to server
            this.startTimer();
        }
        
        this.isRunning = true;
        this.isPaused = false;
        
        this.interval = setInterval(() => {
            this.tick();
        }, 1000);
        
        this.updateButtons();
        this.updateTimerInfo();
        this.hideSetup();
        
        // Add timer active class for animation
        document.querySelector('.card').classList.add('timer-active');
    }
    
    pause() {
        this.isPaused = !this.isPaused;
        
        if (this.isPaused) {
            clearInterval(this.interval);
            this.pauseBtn.innerHTML = '<i class="bi bi-play-fill"></i> Resume';
        } else {
            this.interval = setInterval(() => {
                this.tick();
            }, 1000);
            this.pauseBtn.innerHTML = '<i class="bi bi-pause-fill"></i> Pause';
        }
        
        // Send pause request to server
        this.pauseTimer();
    }
    
    stop() {
        this.isRunning = false;
        this.isPaused = false;
        clearInterval(this.interval);
        
        // Show completion modal
        const modal = new bootstrap.Modal(document.getElementById('completionModal'));
        modal.show();
        
        this.updateButtons();
        document.querySelector('.card').classList.remove('timer-active');
    }
    
    reset() {
        this.isRunning = false;
        this.isPaused = false;
        clearInterval(this.interval);
        
        this.timeLeft = this.duration;
        this.updateDisplay();
        this.updateButtons();
        this.showSetup();
        
        document.querySelector('.card').classList.remove('timer-active');
        
        // Cancel timer on server
        this.cancelTimer();
    }
    
    tick() {
        if (!this.isPaused) {
            this.timeLeft--;
            this.updateDisplay();
            this.updateProgress();
            
            if (this.timeLeft <= 0) {
                this.complete();
            }
        }
    }
    
    complete() {
        this.isRunning = false;
        clearInterval(this.interval);
        
        // Play notification sound
        this.playNotificationSound();
        
        // Show browser notification
        this.showNotification();
        
        // Show completion modal
        const modal = new bootstrap.Modal(document.getElementById('completionModal'));
        modal.show();
        
        this.updateButtons();
        document.querySelector('.card').classList.remove('timer-active');
    }
    
    updateDisplay() {
        const minutes = Math.floor(this.timeLeft / 60);
        const seconds = this.timeLeft % 60;
        
        this.minutesDisplay.textContent = minutes.toString().padStart(2, '0');
        this.secondsDisplay.textContent = seconds.toString().padStart(2, '0');
        
        // Update page title
        document.title = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')} - ${this.taskName || 'Timer'}`;
    }
    
    updateProgress() {
        const progress = ((this.duration - this.timeLeft) / this.duration) * 100;
        this.progressBar.style.width = `${progress}%`;
    }
    
    updateButtons() {
        if (this.isRunning) {
            this.startBtn.style.display = 'none';
            this.pauseBtn.style.display = 'inline-block';
            this.stopBtn.style.display = 'inline-block';
        } else {
            this.startBtn.style.display = 'inline-block';
            this.pauseBtn.style.display = 'none';
            this.stopBtn.style.display = 'none';
        }
    }
    
    updateTimerInfo() {
        this.taskNameDisplay.textContent = this.taskName || 'Ready to Focus';
        this.timerTypeDisplay.textContent = `${this.timerType.charAt(0).toUpperCase() + this.timerType.slice(1)} Session`;
    }
    
    hideSetup() {
        document.getElementById('timer-setup').style.display = 'none';
    }
    
    showSetup() {
        document.getElementById('timer-setup').style.display = 'block';
    }
    
    playNotificationSound() {
        // Create audio context for notification sound
        if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
            const audioContext = new (AudioContext || webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 1);
        }
    }
    
    showNotification() {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Timer Complete!', {
                body: `Your ${this.timerType} session for "${this.taskName}" is complete.`,
                icon: '/static/icons/icon-192x192.png'
            });
        }
    }
    
    // Server communication methods
    startTimer() {
        fetch('/hook/start_timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                task_name: this.taskName,
                duration: Math.floor(this.duration / 60),
                timer_type: this.timerType,
                category: this.category
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'success');
            }
        })
        .catch(error => {
            console.error('Error starting timer:', error);
        });
    }
    
    pauseTimer() {
        fetch('/hook/pause_timer', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'info');
            }
        })
        .catch(error => {
            console.error('Error pausing timer:', error);
        });
    }
    
    cancelTimer() {
        fetch('/hook/cancel_timer', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'info');
            }
        })
        .catch(error => {
            console.error('Error cancelling timer:', error);
        });
    }
    
    completeSession() {
        const mood = document.querySelector('input[name="mood"]:checked').value;
        
        fetch('/hook/complete_timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                mood: mood
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(`${data.message} (+${data.points} points!)`, 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('completionModal'));
                modal.hide();
                
                // Reset timer
                this.reset();
                
                // Redirect to Hook index after a delay
                setTimeout(() => {
                    window.location.href = '/hook/';
                }, 2000);
            }
        })
        .catch(error => {
            console.error('Error completing session:', error);
        });
    }
    
    checkActiveTimer() {
        fetch('/hook/get_timer_status')
        .then(response => response.json())
        .then(data => {
            if (data.active) {
                this.taskName = data.task_name;
                this.timerType = data.timer_type;
                this.timeLeft = Math.floor(data.remaining);
                this.duration = this.timeLeft; // Approximate
                
                this.taskNameInput.value = this.taskName;
                this.updateDisplay();
                this.updateTimerInfo();
                
                if (!data.is_paused) {
                    this.start();
                } else {
                    this.isRunning = true;
                    this.isPaused = true;
                    this.updateButtons();
                    this.hideSetup();
                }
            }
        })
        .catch(error => {
            console.error('Error checking timer status:', error);
        });
    }
}

// Initialize timer when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    // Initialize timer
    new Timer();
});