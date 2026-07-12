const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const selectedFileDiv = document.getElementById('selectedFile');
const startBtn = document.getElementById('startBtn');
const downloadBtn = document.getElementById('downloadBtn');
const terminalContent = document.getElementById('terminal-content');
const terminal = document.getElementById('terminal');

let selectedFile = null;

// Drag and drop handlers
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
});

dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
});

dropzone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', function() {
    handleFiles(this.files);
});

function handleFiles(files) {
    if (files.length > 0) {
        selectedFile = files[0];
        if (selectedFile.name.endsWith('.csv')) {
            selectedFileDiv.textContent = `Selected: ${selectedFile.name}`;
            selectedFileDiv.classList.remove('hidden');
            startBtn.classList.remove('hidden');
            downloadBtn.classList.add('hidden');
        } else {
            alert('Please upload a .csv file');
            selectedFile = null;
        }
    }
}

function appendToTerminal(text) {
    const isScrolledToBottom = terminal.scrollHeight - terminal.clientHeight <= terminal.scrollTop + 10;
    
    // Check if the text contains a carriage return \r (used by tqdm)
    if (text.includes('\r')) {
        // Simple handling: just append it, or we could replace the last line.
        // For simplicity in a web UI, we'll just append it normally or strip \r.
        text = text.replace(/\r/g, '');
    }

    const line = document.createElement('div');
    
    // Colorize output slightly
    if (text.includes('INFO')) line.classList.add('text-blue-400');
    else if (text.includes('WARNING')) line.classList.add('text-amber-400');
    else if (text.includes('ERROR')) line.classList.add('text-rose-400');
    else if (text.includes('Success')) line.classList.add('text-emerald-400');
    
    line.textContent = text;
    terminalContent.appendChild(line);

    if (isScrolledToBottom) {
        terminal.scrollTop = terminal.scrollHeight;
    }
}

startBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    startBtn.disabled = true;
    startBtn.textContent = 'Uploading...';
    startBtn.classList.add('opacity-50', 'cursor-not-allowed');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        terminalContent.innerHTML = '';
        appendToTerminal('Uploading CSV to server...');

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (data.error) {
            appendToTerminal(`ERROR: ${data.error}`);
            resetBtn();
            return;
        }

        startBtn.textContent = 'Running Pipeline...';
        
        // Start Event Source
        const eventSource = new EventSource('/stream');
        
        eventSource.onmessage = function(event) {
            const msg = event.data;
            if (msg === 'DONE') {
                eventSource.close();
                appendToTerminal('\n--- PIPELINE COMPLETE ---');
                startBtn.classList.add('hidden');
                downloadBtn.classList.remove('hidden');
                // Trigger confetti or something
            } else {
                appendToTerminal(msg);
            }
        };

        eventSource.onerror = function() {
            appendToTerminal('Lost connection to server stream.');
            eventSource.close();
            resetBtn();
        };

    } catch (error) {
        appendToTerminal(`ERROR: ${error.message}`);
        resetBtn();
    }
});

downloadBtn.addEventListener('click', () => {
    window.location.href = '/download';
});

function resetBtn() {
    startBtn.disabled = false;
    startBtn.textContent = 'Start Scraping Engine';
    startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
}
