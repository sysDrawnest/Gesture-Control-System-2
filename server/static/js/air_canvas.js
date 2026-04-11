// Air Canvas - Gesture Drawing Application
let socket = null;
let token = localStorage.getItem('token');
let canvas = document.getElementById('drawingCanvas');
let ctx = canvas.getContext('2d');
let isDrawing = false;
let drawingHistory = [];
let currentStep = -1;
let currentColor = '#ff4444';
let currentBrushSize = 5;
let shareRoomId = null;

// Canvas dimensions
canvas.width = 1200;
canvas.height = 700;

// Initialize canvas
ctx.fillStyle = 'white';
ctx.fillRect(0, 0, canvas.width, canvas.height);
saveToHistory();

// Check authentication
if (!token) {
    window.location.href = '/login';
}

// Initialize WebSocket
function initWebSocket() {
    socket = io('/', {
        query: { token: token },
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        document.getElementById('statusDot').className = 'status-dot connected';
        document.getElementById('statusText').textContent = 'Connected';
        updateGestureHint('Connected', '✋');

        // Register as drawing client
        socket.emit('register_drawing_client', {
            device_name: 'AirCanvas'
        });
    });

    socket.on('disconnect', () => {
        document.getElementById('statusDot').className = 'status-dot';
        document.getElementById('statusText').textContent = 'Disconnected';
        updateGestureHint('Reconnecting...', '⚠️');
    });

    socket.on('drawing_stroke', (data) => {
        // Receive drawing strokes from other clients
        drawStroke(data);
    });

    socket.on('drawing_clear', () => {
        // Explicit clear from gesture or remote
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        saveToHistory();
        updateGestureHint('Canvas Cleared (Remote)', '🗑️');
    });

    socket.on('drawing_undo', () => {
        // Explicit undo from gesture or remote
        if (currentStep > 0) {
            currentStep--;
            const img = new Image();
            img.src = drawingHistory[currentStep];
            img.onload = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
            };
            updateGestureHint('Undo (Remote)', '↩️');
        }
    });

    socket.on('drawing_shared', (data) => {
        shareRoomId = data.room_id;
        updateGestureHint('Shared Drawing Active', '🖐️');
        document.getElementById('shareUrl').value = `${window.location.origin}/air_canvas?room=${shareRoomId}`;
    });
}

// Drawing functions
function startDrawing(e) {
    isDrawing = true;
    const pos = getMousePos(e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
}

function draw(e) {
    if (!isDrawing) return;
    const pos = getMousePos(e);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();

    // Send to server for sharing
    if (socket && shareRoomId) {
        socket.emit('drawing_stroke', {
            room_id: shareRoomId,
            x1: pos.x,
            y1: pos.y,
            color: currentColor,
            size: currentBrushSize
        });
    }
}

function stopDrawing() {
    if (isDrawing) {
        isDrawing = false;
        ctx.beginPath();
        saveToHistory();
    }
}

function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    let clientX, clientY;

    if (e.touches) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
    } else {
        clientX = e.clientX;
        clientY = e.clientY;
    }

    return {
        x: (clientX - rect.left) * scaleX,
        y: (clientY - rect.top) * scaleY
    };
}

function drawStroke(data) {
    ctx.beginPath();
    ctx.moveTo(data.x1, data.y1);
    ctx.lineTo(data.x2, data.y2);
    ctx.strokeStyle = data.color;
    ctx.lineWidth = data.size;
    ctx.lineCap = 'round';
    ctx.stroke();
}

function setColor(color) {
    currentColor = color;
    ctx.strokeStyle = color;
    updateGestureHint(`Color: ${color}`, '🎨');
}

function setBrushSize(size) {
    currentBrushSize = size;
    ctx.lineWidth = size;
    updateGestureHint(`Brush: ${size}px`, '✏️');
}

function saveToHistory() {
    const imageData = canvas.toDataURL();
    drawingHistory = drawingHistory.slice(0, currentStep + 1);
    drawingHistory.push(imageData);
    currentStep = drawingHistory.length - 1;
}

function undoLast() {
    if (currentStep > 0) {
        currentStep--;
        const img = new Image();
        img.src = drawingHistory[currentStep];
        img.onload = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);
        };
        updateGestureHint('Undo', '↩️');

        // Broadcast undo to shared session
        if (socket && shareRoomId) {
            socket.emit('drawing_undo', { room_id: shareRoomId });
        }
    }
}

function clearCanvas() {
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    saveToHistory();
    updateGestureHint('Canvas Cleared', '🗑️');

    // Broadcast clear to shared session
    if (socket && shareRoomId) {
        socket.emit('drawing_clear', { room_id: shareRoomId });
    }
}

function updateGestureHint(text, icon) {
    const hint = document.getElementById('gestureHint');
    hint.innerHTML = `<i class="fas ${getIconClass(icon)}"></i><span>${text}</span>`;
}

function getIconClass(icon) {
    const icons = {
        '✋': 'fa-hand-peace',
        '👆': 'fa-hand-point-up',
        '🤏': 'fa-hand-peace',
        '✌️': 'fa-hand-peace',
        '✊': 'fa-hand-fist',
        '🎨': 'fa-palette',
        '✏️': 'fa-pen-fancy',
        '↩️': 'fa-undo',
        '🗑️': 'fa-trash'
    };
    return icons[icon] || 'fa-hand-peace';
}

// Save drawing to server
async function saveDrawing() {
    const imageData = canvas.toDataURL('image/png');
    const drawingName = prompt('Enter a name for your drawing:', `Drawing_${new Date().toLocaleString()}`);

    if (drawingName) {
        try {
            const response = await fetch('/api/drawings/save', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: drawingName,
                    image_data: imageData
                })
            });

            const data = await response.json();
            if (data.success) {
                alert('Drawing saved to gallery!');
                updateGestureHint('Drawing Saved!', '💾');
            } else {
                alert('Error saving drawing: ' + data.error);
            }
        } catch (error) {
            console.error('Error saving drawing:', error);
            alert('Error saving drawing');
        }
    }
}

// Export as PNG
function exportAsImage() {
    const link = document.createElement('a');
    link.download = `air_canvas_${Date.now()}.png`;
    link.href = canvas.toDataURL();
    link.click();
    updateGestureHint('Exported as PNG', '📸');
}

// Export as PDF
async function exportAsPDF() {
    const { jsPDF } = window.jspdf;
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'px',
        format: [canvas.width, canvas.height]
    });
    pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
    pdf.save(`air_canvas_${Date.now()}.pdf`);
    updateGestureHint('Exported as PDF', '📄');
}

// Share canvas
function shareCanvas() {
    if (socket) {
        socket.emit('share_drawing', {});
        document.getElementById('shareModal').style.display = 'block';
    }
}

// Load gallery
async function loadGallery() {
    try {
        const response = await fetch('/api/drawings/list', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();

        if (data.success) {
            const gallery = document.getElementById('galleryList');
            gallery.innerHTML = data.drawings.map(drawing => `
                <div class="gallery-item" onclick="loadDrawing(${drawing.id})">
                    <img src="${drawing.image_data}" alt="${drawing.name}">
                    <div class="gallery-item-info">
                        <strong>${drawing.name}</strong><br>
                        <small>${new Date(drawing.created_at).toLocaleString()}</small>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading gallery:', error);
    }
}

function loadDrawing(drawingId) {
    // Load drawing into canvas
    fetch(`/api/drawings/${drawingId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const img = new Image();
                img.src = data.drawing.image_data;
                img.onload = () => {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    saveToHistory();
                };
                document.getElementById('galleryModal').style.display = 'none';
                updateGestureHint('Loaded from Gallery', '🖼️');
            }
        });
}

// Event Listeners
canvas.addEventListener('mousedown', startDrawing);
canvas.addEventListener('mousemove', draw);
canvas.addEventListener('mouseup', stopDrawing);
canvas.addEventListener('mouseleave', stopDrawing);

// Touch events for mobile
canvas.addEventListener('touchstart', startDrawing);
canvas.addEventListener('touchmove', draw);
canvas.addEventListener('touchend', stopDrawing);

// Tool buttons
document.getElementById('colorRed').addEventListener('click', () => setColor('#ff4444'));
document.getElementById('colorBlue').addEventListener('click', () => setColor('#4444ff'));
document.getElementById('colorGreen').addEventListener('click', () => setColor('#44ff44'));
document.getElementById('colorYellow').addEventListener('click', () => setColor('#ffaa44'));
document.getElementById('colorPurple').addEventListener('click', () => setColor('#aa44ff'));

document.getElementById('brushSmall').addEventListener('click', () => setBrushSize(3));
document.getElementById('brushMedium').addEventListener('click', () => setBrushSize(8));
document.getElementById('brushLarge').addEventListener('click', () => setBrushSize(15));

document.getElementById('undoBtn').addEventListener('click', undoLast);
document.getElementById('clearBtn').addEventListener('click', clearCanvas);
document.getElementById('saveDrawingBtn').addEventListener('click', saveDrawing);
document.getElementById('exportImageBtn').addEventListener('click', exportAsImage);
document.getElementById('exportPdfBtn').addEventListener('click', exportAsPDF);
document.getElementById('shareCanvasBtn').addEventListener('click', shareCanvas);
document.getElementById('galleryBtn').addEventListener('click', () => {
    loadGallery();
    document.getElementById('galleryModal').style.display = 'block';
});

// Modal handling
document.querySelectorAll('.close').forEach(close => {
    close.addEventListener('click', () => {
        document.getElementById('galleryModal').style.display = 'none';
        document.getElementById('shareModal').style.display = 'none';
    });
});

document.getElementById('copyUrlBtn').addEventListener('click', () => {
    const urlInput = document.getElementById('shareUrl');
    urlInput.select();
    document.execCommand('copy');
    alert('URL copied to clipboard!');
});

// Logout
document.getElementById('logoutBtn').addEventListener('click', async () => {
    await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (socket) socket.disconnect();
    localStorage.removeItem('token');
    window.location.href = '/login';
});

// Initialize
initWebSocket();
setBrushSize(5);
setColor('#ff4444');