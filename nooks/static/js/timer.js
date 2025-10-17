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
        
        // Focus Lock properties
        this.distractionDomains = [];
        this.focusLockDismissed = false;
        this.focusLockDismissTime = null;
        this.focusLockInterval = null;
        
        // Hook-Nook integration properties
        this.linkedBook = null;
        this.isReadingSession = false;
        this.userBooks = [];
        
        this.initializeElements();
        this.bindEvents();
        this.initializeFocusLock();
        this.loadUserBooks();
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
        
        // Focus Lock elements
        this.focusLockWidget = document.getElementById('focus-lock-widget');
        this.focusLockMessage = document.getElementById('focus-lock-message');
        this.dismissFocusLockBtn = document.getElementById('dismiss-focus-lock');
        this.distractionDomainsInput = document.getElementById('distraction-domains');
        this.saveDistractionListBtn = document.getElementById('save-distraction-list');
        this.loadDistractionListBtn = document.getElementById('load-distraction-list');
        this.currentDomainsDiv = document.getElementById('current-domains');
        this.domainsListDiv = document.getElementById('domains-list');
        
        // Hook-Nook integration elements
        this.isReadingSessionCheckbox = document.getElementById('is_reading_session');
        this.bookSelectionDiv = document.getElementById('book-selection');
        this.linkedBookSelect = document.getElementById('linked_book_id');
        this.readingSessionBtn = document.getElementById('reading-session-btn');
        this.readingProgressSection = document.getElementById('reading-progress-section');
        this.linkedBookTitle = document.getElementById('linked-book-title');
        this.pagesReadInput = document.getElementById('pages_read');
        this.currentPageInput = document.getElementById('current_page');
        this.pageProgressText = document.getElementById('page-progress-text');
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
        
        // Focus Lock event listeners
        if (this.dismissFocusLockBtn) {
            this.dismissFocusLockBtn.addEventListener('click', () => {
                this.dismissFocusLock();
            });
        }
        
        if (this.saveDistractionListBtn) {
            this.saveDistractionListBtn.addEventListener('click', () => {
                this.saveDistractionList();
            });
        }
        
        if (this.loadDistractionListBtn) {
            this.loadDistractionListBtn.addEventListener('click', () => {
                this.loadDistractionList();
            });
        }
        
        // Hook-Nook integration event listeners
        if (this.isReadingSessionCheckbox) {
            this.isReadingSessionCheckbox.addEventListener('change', () => {
                this.toggleBookSelection();
            });
        }
        
        if (this.linkedBookSelect) {
            this.linkedBookSelect.addEventListener('change', () => {
                this.updateSelectedBook();
            });
        }
        
        if (this.readingSessionBtn) {
            this.readingSessionBtn.addEventListener('click', () => {
                this.showReadingSessionModal();
            });
        }
        
        if (this.currentPageInput) {
            this.currentPageInput.addEventListener('input', () => {
                this.updatePageProgress();
            });
        }
        
        if (this.pagesReadInput) {
            this.pagesReadInput.addEventListener('input', () => {
                this.updatePagesRead();
            });
        }
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
            
            // Check if this is a reading session
            if (this.isReadingSessionCheckbox && this.isReadingSessionCheckbox.checked) {
                this.isReadingSession = true;
                if (this.linkedBookSelect && this.linkedBookSelect.value) {
                    this.updateSelectedBook();
                }
            }
            
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
        
        // Hide Focus Lock widget
        this.hideFocusLockWidget();
        this.focusLockDismissed = false;
        
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
        
        // Hide Focus Lock widget
        this.hideFocusLockWidget();
        this.focusLockDismissed = false;
        
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
        
        // Hide Focus Lock widget
        this.hideFocusLockWidget();
        this.focusLockDismissed = false;
        
        // Setup reading completion if this is a reading session
        if (this.isReadingSession && this.linkedBook) {
            this.setupReadingCompletion();
        }
        
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
    
    // Focus Lock methods
    initializeFocusLock() {
        this.loadDistractionList();
    }
    
    showFocusLockWidget() {
        if (this.distractionDomains.length === 0 || this.focusLockDismissed) {
            return;
        }
        
        // Update message with random domains
        let message = 'Remember to avoid distracting sites during your focus session';
        if (this.distractionDomains.length > 0) {
            const randomDomains = this.getRandomDomains(3);
            if (randomDomains.length > 0) {
                message = `Stay focused! Avoid: ${randomDomains.join(', ')}`;
                if (this.distractionDomains.length > 3) {
                    message += ` (+${this.distractionDomains.length - 3} more)`;
                }
            }
        }
        
        this.focusLockMessage.textContent = message;
        this.focusLockWidget.style.display = 'block';
        
        // Set up periodic message updates
        if (this.focusLockInterval) {
            clearInterval(this.focusLockInterval);
        }
        
        this.focusLockInterval = setInterval(() => {
            if (this.isRunning && !this.focusLockDismissed) {
                const randomDomains = this.getRandomDomains(3);
                if (randomDomains.length > 0) {
                    let newMessage = `Stay focused! Avoid: ${randomDomains.join(', ')}`;
                    if (this.distractionDomains.length > 3) {
                        newMessage += ` (+${this.distractionDomains.length - 3} more)`;
                    }
                    this.focusLockMessage.textContent = newMessage;
                }
            }
        }, 30000); // Update every 30 seconds
    }
    
    hideFocusLockWidget() {
        this.focusLockWidget.style.display = 'none';
        if (this.focusLockInterval) {
            clearInterval(this.focusLockInterval);
            this.focusLockInterval = null;
        }
    }
    
    dismissFocusLock() {
        this.focusLockDismissed = true;
        this.focusLockDismissTime = Date.now();
        this.hideFocusLockWidget();
        
        // Re-enable after 5 minutes
        setTimeout(() => {
            this.focusLockDismissed = false;
            if (this.isRunning) {
                this.showFocusLockWidget();
            }
        }, 5 * 60 * 1000);
        
        showToast('Focus Lock dismissed for 5 minutes', 'info');
    }
    
    getRandomDomains(count) {
        if (this.distractionDomains.length === 0) return [];
        
        const shuffled = [...this.distractionDomains].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, Math.min(count, shuffled.length));
    }
    
    saveDistractionList() {
        const domainsText = this.distractionDomainsInput.value.trim();
        const domains = domainsText.split(',').map(d => d.trim()).filter(d => d.length > 0);
        
        fetch('/hook/update_distraction_list', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                domains: domains
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.distractionDomains = data.domains;
                showToast(data.message, 'success');
                this.displayCurrentDomains();
            } else {
                showToast('Error saving distraction list', 'error');
            }
        })
        .catch(error => {
            console.error('Error saving distraction list:', error);
            showToast('Error saving distraction list', 'error');
        });
    }
    
    loadDistractionList() {
        fetch('/hook/get_distraction_list')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.distractionDomains = data.domains;
                if (this.distractionDomainsInput) {
                    this.distractionDomainsInput.value = data.domains.join(', ');
                }
                this.displayCurrentDomains();
            }
        })
        .catch(error => {
            console.error('Error loading distraction list:', error);
        });
    }
    
    displayCurrentDomains() {
        if (this.distractionDomains.length > 0) {
            this.domainsListDiv.innerHTML = this.distractionDomains
                .map(domain => `<span class="badge bg-secondary me-1">${domain}</span>`)
                .join('');
            this.currentDomainsDiv.style.display = 'block';
        } else {
            this.currentDomainsDiv.style.display = 'none';
        }
    }
    
    // Hook-Nook integration methods
    loadUserBooks() {
        fetch('/hook/get_user_books')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.userBooks = data.books;
                this.populateBookSelect();
            }
        })
        .catch(error => {
            console.error('Error loading user books:', error);
        });
    }
    
    populateBookSelect() {
        if (!this.linkedBookSelect) return;
        
        // Clear existing options except the first one
        this.linkedBookSelect.innerHTML = '<option value="">Choose a book...</option>';
        
        this.userBooks.forEach(book => {
            const option = document.createElement('option');
            option.value = book.id;
            option.textContent = `${book.title} (${book.current_page}/${book.page_count} pages)`;
            option.dataset.currentPage = book.current_page;
            option.dataset.pageCount = book.page_count;
            option.dataset.title = book.title;
            this.linkedBookSelect.appendChild(option);
        });
    }
    
    toggleBookSelection() {
        if (!this.bookSelectionDiv) return;
        
        if (this.isReadingSessionCheckbox.checked) {
            this.bookSelectionDiv.style.display = 'block';
            this.categoryInput.value = 'reading';
            this.isReadingSession = true;
        } else {
            this.bookSelectionDiv.style.display = 'none';
            this.isReadingSession = false;
            this.linkedBook = null;
        }
    }
    
    updateSelectedBook() {
        const selectedOption = this.linkedBookSelect.selectedOptions[0];
        if (selectedOption && selectedOption.value) {
            this.linkedBook = {
                id: selectedOption.value,
                title: selectedOption.dataset.title,
                current_page: parseInt(selectedOption.dataset.currentPage),
                page_count: parseInt(selectedOption.dataset.pageCount)
            };
            
            // Auto-fill task name
            this.taskNameInput.value = `Reading: ${this.linkedBook.title}`;
        } else {
            this.linkedBook = null;
        }
    }
    
    showReadingSessionModal() {
        // Create a simple modal to select book and start reading session
        if (this.userBooks.length === 0) {
            showToast('No books found. Add some books in Nook first!', 'warning');
            return;
        }
        
        const bookOptions = this.userBooks.map(book => 
            `<option value="${book.id}">${book.title} (${book.current_page}/${book.page_count})</option>`
        ).join('');
        
        const modalHtml = `
            <div class="modal fade" id="readingSessionModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-book text-info me-2"></i>Start Reading Session
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Select Book</label>
                                <select class="form-select" id="modal-book-select">
                                    ${bookOptions}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Duration (minutes)</label>
                                <input type="number" class="form-control" id="modal-duration" value="25" min="5" max="120">
                            </div>
                            <div class="alert alert-info">
                                <i class="bi bi-star text-warning me-1"></i>
                                <strong>Bonus Points:</strong> Earn extra points for focused reading sessions!
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-info" id="start-reading-session">Start Session</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('readingSessionModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('readingSessionModal'));
        modal.show();
        
        // Handle start button
        document.getElementById('start-reading-session').addEventListener('click', () => {
            const bookId = document.getElementById('modal-book-select').value;
            const duration = document.getElementById('modal-duration').value;
            
            if (!bookId) {
                showToast('Please select a book', 'warning');
                return;
            }
            
            this.startReadingSession(bookId, duration);
            modal.hide();
        });
    }
    
    startReadingSession(bookId, duration) {
        fetch('/hook/start_reading_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                book_id: bookId,
                duration: duration
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'success');
                
                // Update timer state
                this.linkedBook = data.book;
                this.isReadingSession = true;
                this.taskName = `Reading: ${data.book.title}`;
                this.duration = parseInt(duration) * 60;
                this.timeLeft = this.duration;
                this.timerType = 'work';
                this.category = 'reading';
                
                // Update distraction domains
                if (data.distraction_domains) {
                    this.distractionDomains = data.distraction_domains;
                }
                
                // Start the timer
                this.isRunning = true;
                this.interval = setInterval(() => {
                    this.tick();
                }, 1000);
                
                this.updateDisplay();
                this.updateTimerInfo();
                this.updateButtons();
                this.hideSetup();
                this.showFocusLockWidget();
                
                document.querySelector('.card').classList.add('timer-active');
            } else {
                showToast(data.message || 'Failed to start reading session', 'error');
            }
        })
        .catch(error => {
            console.error('Error starting reading session:', error);
            showToast('Failed to start reading session', 'error');
        });
    }
    
    updatePageProgress() {
        if (!this.linkedBook || !this.currentPageInput || !this.pageProgressText) return;
        
        const currentPage = parseInt(this.currentPageInput.value) || 0;
        const progress = Math.round((currentPage / this.linkedBook.page_count) * 100);
        this.pageProgressText.textContent = `Progress: ${progress}%`;
    }
    
    updatePagesRead() {
        if (!this.linkedBook || !this.pagesReadInput || !this.currentPageInput) return;
        
        const pagesRead = parseInt(this.pagesReadInput.value) || 0;
        const newCurrentPage = this.linkedBook.current_page + pagesRead;
        this.currentPageInput.value = Math.min(newCurrentPage, this.linkedBook.page_count);
        this.updatePageProgress();
    }
    
    setupReadingCompletion() {
        if (!this.linkedBook || !this.readingProgressSection) return;
        
        // Show reading progress section
        this.readingProgressSection.style.display = 'block';
        this.linkedBookTitle.textContent = `Reading: ${this.linkedBook.title}`;
        
        // Set initial values
        this.currentPageInput.value = this.linkedBook.current_page;
        this.pagesReadInput.value = 0;
        this.updatePageProgress();
    }

    // Server communication methods
    startTimer() {
        const formData = {
            task_name: this.taskName,
            duration: Math.floor(this.duration / 60),
            timer_type: this.timerType,
            category: this.category,
            is_reading_session: this.isReadingSession ? 'true' : 'false'
        };
        
        // Add book data if linked
        if (this.linkedBook && this.linkedBook.id) {
            formData.linked_book_id = this.linkedBook.id;
        }
        
        fetch('/hook/start_timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'success');
                
                // Update distraction domains from server response
                if (data.distraction_domains) {
                    this.distractionDomains = data.distraction_domains;
                }
                
                // Update linked book data from server
                if (data.linked_book) {
                    this.linkedBook = data.linked_book;
                }
                
                // Show Focus Lock widget if timer is work type
                if (this.timerType === 'work') {
                    this.showFocusLockWidget();
                }
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
        const productivityRating = document.getElementById('productivity_rating').value;
        
        const formData = {
            mood: mood,
            productivity_rating: productivityRating
        };
        
        // Add reading progress if this is a reading session
        if (this.isReadingSession && this.linkedBook) {
            formData.pages_read = this.pagesReadInput ? this.pagesReadInput.value : '0';
            formData.current_page = this.currentPageInput ? this.currentPageInput.value : this.linkedBook.current_page.toString();
        }
        
        fetch('/hook/complete_timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                let message = `${data.message} (+${data.points} points!)`;
                
                // Add reading bonus message
                if (data.reading_bonus && data.reading_bonus > 0) {
                    message += ` Including ${data.reading_bonus} bonus points for focused reading!`;
                }
                
                showToast(message, 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('completionModal'));
                modal.hide();
                
                // Reset timer
                this.reset();
                
                // Redirect based on session type
                setTimeout(() => {
                    if (data.linked_module === 'nook') {
                        window.location.href = '/nook/';
                    } else {
                        window.location.href = '/hook/';
                    }
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