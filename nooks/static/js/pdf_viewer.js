// PDF.js loader for Nooks App
// Place this in static/js/pdf_viewer.js

// Assumes PDF.js is loaded via CDN in the template
let pdfDoc = null;
let pageNum = 1;
let pageRendering = false;
let pageNumPending = null;
let scale = 1.2;
let canvas = null;
let ctx = null;
let bookId = null;

function renderPage(num) {
    pageRendering = true;
    pdfDoc.getPage(num).then(function(page) {
        let viewport = page.getViewport({ scale: scale });
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        // Render PDF page into canvas context
        let renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };
        let renderTask = page.render(renderContext);

        // Wait for rendering to finish
        renderTask.promise.then(function() {
            pageRendering = false;
            if (pageNumPending !== null) {
                renderPage(pageNumPending);
                pageNumPending = null;
            }
            // Update progress in backend
            updateReadingProgress(num);
        });
    });

    // Update page counters
    document.getElementById('page_num').textContent = num;
    document.getElementById('page_count').textContent = pdfDoc.numPages;
}

function queueRenderPage(num) {
    if (pageRendering) {
        pageNumPending = num;
    } else {
        renderPage(num);
    }
}

function onPrevPage() {
    if (pageNum <= 1) {
        return;
    }
    pageNum--;
    queueRenderPage(pageNum);
}

function onNextPage() {
    if (pageNum >= pdfDoc.numPages) {
        return;
    }
    pageNum++;
    queueRenderPage(pageNum);
}

function updateReadingProgress(page) {
    // Send AJAX request to backend to update current page
    fetch(`/nook/update_progress_ajax/${bookId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrf_token || ''
        },
        body: JSON.stringify({ current_page: page })
    });
}

function extractSelectedText() {
    let selection = window.getSelection().toString();
    if (selection.length > 0) {
        document.getElementById('quote_text').value = selection;
        document.getElementById('quote_page').value = pageNum;
        let quoteModal = new bootstrap.Modal(document.getElementById('quoteModal'));
        quoteModal.show();
    }
}

function setupPdfViewer(pdfUrl, book_id) {
    bookId = book_id;
    canvas = document.getElementById('the-canvas');
    ctx = canvas.getContext('2d');

    pdfjsLib.getDocument(pdfUrl).promise.then(function(pdfDoc_) {
        pdfDoc = pdfDoc_;
        document.getElementById('page_count').textContent = pdfDoc.numPages;
        renderPage(pageNum);
    });

    document.getElementById('prev').addEventListener('click', onPrevPage);
    document.getElementById('next').addEventListener('click', onNextPage);
    canvas.addEventListener('mouseup', extractSelectedText);
}
