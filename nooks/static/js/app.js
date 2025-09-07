// Main application JavaScript

// Service Worker Registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// PWA Install Prompt
let deferredPrompt;
const installButton = document.getElementById('install-button');

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    if (installButton) {
        installButton.style.display = 'block';
        installButton.addEventListener('click', () => {
            installButton.style.display = 'none';
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('User accepted the install prompt');
                }
                deferredPrompt = null;
            });
        });
    }
});

// Online/Offline Status
window.addEventListener('online', () => {
    document.body.classList.remove('offline');
    showToast('Back online!', 'success');
});

window.addEventListener('offline', () => {
    document.body.classList.add('offline');
    showToast('You are offline', 'warning');
});

// Toast Notifications
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Theme Switcher
function switchTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem('theme', theme);
}

// Load saved theme
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    switchTheme(savedTheme);
});

// Auto-save forms
function autoSave(formId, key) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    // Load saved data
    const savedData = localStorage.getItem(key);
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) field.value = data[fieldName];
        });
    }
    
    // Save on input
    form.addEventListener('input', () => {
        const formData = new FormData(form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        localStorage.setItem(key, JSON.stringify(data));
    });
    
    // Clear on submit
    form.addEventListener('submit', () => {
        localStorage.removeItem(key);
    });
}

// Utility functions
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function formatDuration(minutes) {
    if (minutes < 60) {
        return `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

// Book search functionality
function searchBooks(query) {
    if (query.length < 3) return;
    
    fetch(`/nook/search_books?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(books => {
            displayBookSearchResults(books);
        })
        .catch(error => {
            console.error('Error searching books:', error);
            showToast('Error searching books', 'danger');
        });
}

function displayBookSearchResults(books) {
    const resultsContainer = document.getElementById('book-search-results');
    if (!resultsContainer) return;
    
    resultsContainer.innerHTML = '';
    
    books.forEach(book => {
        const bookElement = document.createElement('div');
        bookElement.className = 'col-md-6 mb-3';
        bookElement.innerHTML = `
            <div class="card">
                <div class="row g-0">
                    <div class="col-4">
                        <img src="${book.cover_image}" class="img-fluid rounded-start h-100 object-fit-cover" alt="${book.title}">
                    </div>
                    <div class="col-8">
                        <div class="card-body">
                            <h6 class="card-title">${book.title}</h6>
                            <p class="card-text text-muted small">by ${book.authors.join(', ')}</p>
                            <button class="btn btn-success btn-sm" onclick="selectBook('${book.google_books_id}', '${book.title}', '${book.authors.join(', ')}', '${book.description}', '${book.cover_image}', ${book.page_count})">
                                Select
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        resultsContainer.appendChild(bookElement);
    });
}

function selectBook(googleBooksId, title, authors, description, coverImage, pageCount) {
    document.getElementById('google_books_id').value = googleBooksId;
    document.getElementById('title').value = title;
    document.getElementById('authors').value = authors;
    document.getElementById('description').value = description;
    document.getElementById('cover_image').value = coverImage;
    document.getElementById('page_count').value = pageCount;
    
    // Hide search results
    document.getElementById('book-search-results').innerHTML = '';
    document.getElementById('search-query').value = '';
}

// Initialize auto-save for common forms
document.addEventListener('DOMContentLoaded', () => {
    autoSave('add-book-form', 'add-book-draft');
    autoSave('timer-form', 'timer-draft');
});