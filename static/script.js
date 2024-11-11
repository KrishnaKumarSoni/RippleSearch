const sessionId = Math.random().toString(36).substring(7);
let eventSource = null;

function logToConsole(message, type = 'info') {
    const consoleOutput = document.getElementById('console-output');
    if (!consoleOutput) return;

    const line = document.createElement('div');
    line.className = `console-line ${type}`;
    line.textContent = message;
    consoleOutput.appendChild(line);
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function handleConsoleCommand(command) {
    const [action, ...args] = command.toLowerCase().trim().split(' ');
    
    switch (action) {
        case 'help':
            logToConsole(`Available commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
scrape [location] [search]  Start scraping
pause                       Pause scraping
stop                       Stop scraping
help                       Show this help

Example: scrape bangalore law firms`, 'info');
            break;
            
        case 'scrape':
            if (args.length < 2) {
                logToConsole('Error: Please provide both location and search terms', 'error');
                return;
            }
            const location = args[0];
            const search = args.slice(1).join(' ');
            
            // Generate a session ID
            const sessionId = Date.now().toString();
            
            // Initialize event source first
            initEventSource(sessionId);
            
            fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    location,
                    search,
                    session_id: sessionId
                })
            });
            break;
            
        case 'pause':
            fetch('/api/pause', { method: 'POST' })
                .then(() => logToConsole('Scraping paused', 'warning'));
            break;
            
        case 'stop':
            fetch('/api/stop', { method: 'POST' })
                .then(() => logToConsole('Scraping stopped', 'info'));
            break;
            
        default:
            logToConsole(`Unknown command: ${action}\nType 'help' to see available commands`, 'error');
            break;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const consoleInput = document.querySelector('.console-input');
    const clearButton = document.getElementById('clearConsole');
    
    if (consoleInput) {
        consoleInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const command = e.target.value.trim();
                if (command) {
                    logToConsole(`> ${command}`, 'command');
                    handleConsoleCommand(command);
                    e.target.value = '';
                }
            }
        });
    }

    if (clearButton) {
        clearButton.addEventListener('click', () => {
            const consoleOutput = document.getElementById('console-output');
            if (consoleOutput) consoleOutput.innerHTML = '';
        });
    }

    // Add Export CSV handler
    const exportButton = document.querySelector('.export-csv');
    if (exportButton) {
        exportButton.addEventListener('click', () => {
            const tbody = document.getElementById('resultsList');
            if (!tbody || !tbody.children.length) {
                logToConsole('No data to export', 'error');
                return;
            }
            
            fetch('/api/export-current', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `export_${Date.now()}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            })
            .catch(error => logToConsole('Export failed: ' + error, 'error'));
        });
    }

    const exportBtn = document.getElementById('exportCSV');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportToCSV);
    }
});

function startScraping(location, search) {
    const url = `/api/scrape?location=${encodeURIComponent(location)}&search=${encodeURIComponent(search)}`;
    
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource(url);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.message) {
            logToConsole(data.message, data.type || 'info');
        }
        if (data.total_leads) {
            document.getElementById('totalLeads').textContent = data.total_leads;
        }
        if (data.pages_scraped) {
            document.getElementById('pagesScraped').textContent = data.pages_scraped;
        }
        if (data.results) {
            updateResultsTable(data.results);
        }
    };

    eventSource.onerror = () => {
        logToConsole('Connection lost. Scraping stopped.', 'error');
        eventSource.close();
    };
}

function pauseScraping() {
    fetch('/api/pause', { method: 'POST' });
}

function stopScraping() {
    if (eventSource) {
        eventSource.close();
    }
    fetch('/api/stop', { method: 'POST' });
}

async function fetchWithRetry(url, options, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            if (i === retries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
        }
    }
}

// Initialize EventSource for live updates
function initEventSource(sessionId) {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource(`/api/stream/${sessionId}`);
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'heartbeat') return;
            
            if (data.message) {
                logToConsole(data.message, data.type || 'info');
            }
            
            if (data.results) {
                updateResultsTable(data.results);
            }
            
            if (data.total_leads !== undefined) {
                document.getElementById('totalLeads').textContent = data.total_leads;
            }
            if (data.pages_scraped !== undefined) {
                document.getElementById('pagesScraped').textContent = data.pages_scraped;
            }
        } catch (error) {
            console.error('Error processing message:', error);
        }
    };
    
    eventSource.onerror = function() {
        console.error('EventSource error');
        eventSource.close();
    };
}

function updateDownloadLinks() {
    fetch('/api/downloads')
        .then(response => response.json())
        .then(files => {
            const downloadLinks = document.getElementById('downloadLinks');
            if (!downloadLinks) return;
            
            downloadLinks.innerHTML = files.length ? 
                '<h4>Downloaded Files:</h4>' : 
                '<p>No files available</p>';
                
            files.forEach(file => {
                const link = document.createElement('a');
                link.href = `/api/download/${file}`;
                link.textContent = file;
                downloadLinks.appendChild(link);
            });
        })
        .catch(error => console.error('Error fetching downloads:', error));
}

function updateResultsTable(results) {
    const tbody = document.getElementById('resultsList');
    if (!tbody) return;
    
    results.forEach(result => {
        const row = document.createElement('tr');
        const phone = result.phone ? result.phone.trim() : '';
        
        row.innerHTML = `
            <td>${result.name || '-'}</td>
            <td>${result.address || '-'}</td>
            <td>${phone || '-'}</td>
            <td>${result.rating ? result.rating + ' ⭐' : '-'}</td>
            <td>
                ${phone ? 
                    `<button class="copy-phone" onclick="copyToClipboard('${phone}')">
                        Copy Phone
                    </button>` : 
                    '-'
                }
            </td>
        `;
        tbody.appendChild(row);
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => {
            logToConsole('Phone number copied!', 'success');
        })
        .catch(err => {
            logToConsole('Failed to copy phone number', 'error');
            console.error('Copy failed:', err);
        });
}

function exportToCSV() {
    const tbody = document.getElementById('resultsList');
    if (!tbody || !tbody.rows.length) {
        logToConsole('No data to export', 'error');
        return;
    }

    const rows = Array.from(tbody.rows);
    const headers = ['Business Name', 'Address', 'Phone', 'Rating'];
    
    let csvContent = headers.join(',') + '\n';
    
    rows.forEach(row => {
        const rowData = Array.from(row.cells)
            .slice(0, 4) // Skip the Actions column
            .map(cell => {
                // Escape quotes and wrap in quotes if contains comma
                let text = cell.textContent.replace(/"/g, '""');
                return text.includes(',') ? `"${text}"` : text;
            });
        csvContent += rowData.join(',') + '\n';
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', 'business_listings.csv');
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    logToConsole('CSV file exported successfully', 'success');
}