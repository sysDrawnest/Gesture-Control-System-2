/**
 * UX Settings Manager - Sound, Voice, Haptics, Calibration
 * Fully functional with real feedback....version 3 for 18 april
 * Tutorial functionality moved to standalone tutorial.html
 */

class UXSettingsManager {
    constructor() {
        this.settings = {
            sound: {
                enabled: true,
                volume: 0.7,
                sounds: {
                    click: null,
                    gesture: null,
                    success: null,
                    error: null,
                    notification: null
                }
            },
            voice: {
                enabled: false,
                rate: 1.0,
                pitch: 1.0,
                volume: 1.0,
                voice: null
            },
            haptics: {
                enabled: false,
                intensity: 0.5,
                duration: 50
            },
            tutorial: {
                completed: false,
                currentStep: 0
            },
            calibration: {
                completed: false,
                handSize: 'medium',
                sensitivity: 0.7,
                smoothing: 0.5
            }
        };

        this.speechSynthesis = window.speechSynthesis;
        this.voices = [];
        this.audioContext = null;
        this.init();
    }

    async init() {
        await this.loadSettings();
        this.initAudioContext();
        this.initSounds();
        this.initVoices();
        this.initHaptics();
        this.createSettingsUI();
        this.setupEventListeners();
        this.checkFirstTimeUser();
    }

    initAudioContext() {
        // Create audio context on user interaction to comply with browser policies
        document.addEventListener('click', () => {
            if (!this.audioContext && this.settings.sound.enabled) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                if (this.audioContext.state === 'suspended') {
                    this.audioContext.resume();
                }
            }
        }, { once: true });
    }

    loadSettings() {
        const saved = localStorage.getItem('ux_settings');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                this.settings = { ...this.settings, ...parsed };
            } catch (e) { }
        }
    }

    saveSettings() {
        localStorage.setItem('ux_settings', JSON.stringify(this.settings));
        this.updateUI();
    }

    initSounds() {
        const soundNames = ['click', 'gesture', 'success', 'error', 'notification'];
        for (const name of soundNames) {
            try {
                const audio = new Audio();
                audio.volume = this.settings.sound.volume;
                this.settings.sound.sounds[name] = audio;
            } catch (e) {
                console.warn(`Could not load sound: ${name}`, e);
            }
        }
    }

    generateBeep(frequency, duration, type = 'sine') {
        if (!this.audioContext || !this.settings.sound.enabled) return;
        try {
            const now = this.audioContext.currentTime;
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            oscillator.frequency.value = frequency;
            oscillator.type = type;
            gainNode.gain.setValueAtTime(0.3, now);
            gainNode.gain.exponentialRampToValueAtTime(0.0001, now + duration);
            oscillator.start();
            oscillator.stop(now + duration);
        } catch (e) {
            console.log('Audio play failed:', e);
        }
    }

    playSound(soundName) {
        if (!this.settings.sound.enabled) return;
        if (soundName === 'click') {
            this.generateBeep(800, 0.08, 'sine');
        } else if (soundName === 'gesture') {
            this.generateBeep(600, 0.12, 'sine');
        } else if (soundName === 'success') {
            this.generateBeep(800, 0.08, 'sine');
            setTimeout(() => this.generateBeep(1000, 0.08, 'sine'), 100);
        } else if (soundName === 'error') {
            this.generateBeep(400, 0.15, 'sawtooth');
        } else if (soundName === 'notification') {
            this.generateBeep(500, 0.1, 'sine');
        }
    }

    initVoices() {
        if (this.speechSynthesis) {
            const loadVoices = () => {
                this.voices = this.speechSynthesis.getVoices();
                if (this.voices.length > 0) {
                    const defaultVoice = this.voices.find(v => v.lang === 'en-US' && v.name.includes('Google')) || this.voices[0];
                    this.settings.voice.voice = defaultVoice;
                }
            };
            loadVoices();
            if (this.speechSynthesis.onvoiceschanged !== undefined) {
                this.speechSynthesis.onvoiceschanged = loadVoices;
            }
        }
    }

    speak(text, priority = false) {
        if (!this.settings.voice.enabled || !this.speechSynthesis) return;
        if (priority) {
            this.speechSynthesis.cancel();
        }
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = this.settings.voice.rate;
        utterance.pitch = this.settings.voice.pitch;
        utterance.volume = this.settings.voice.volume;
        if (this.settings.voice.voice) {
            utterance.voice = this.settings.voice.voice;
        }
        this.speechSynthesis.speak(utterance);
    }

    initHaptics() {
        if (!('vibrate' in navigator)) {
            console.log('Vibration not supported');
            this.settings.haptics.enabled = false;
        }
    }

    vibrate(pattern) {
        if (!this.settings.haptics.enabled) return;
        if (!navigator.vibrate) return;
        let vibratePattern;
        if (typeof pattern === 'number') {
            vibratePattern = pattern;
        } else if (pattern === 'click') {
            vibratePattern = 20;
        } else if (pattern === 'gesture') {
            vibratePattern = [30, 50, 30];
        } else if (pattern === 'success') {
            vibratePattern = [50, 100, 50];
        } else if (pattern === 'error') {
            vibratePattern = [100, 50, 100];
        } else {
            vibratePattern = pattern || 50;
        }
        try {
            navigator.vibrate(vibratePattern);
        } catch (e) { }
    }

    createSettingsUI() {
        if (document.getElementById('uxSettingsModal')) return;
        const settingsHTML = `
            <div id="uxSettingsModal" class="modal ux-settings-modal" style="display: none;">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2><i class="fas fa-sliders-h"></i> UX Settings</h2>
                        <button class="close-modal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <!-- Sound Settings -->
                        <div class="settings-section">
                            <h3><i class="fas fa-volume-up"></i> Sound</h3>
                            <div class="setting-item">
                                <label class="switch">
                                    <input type="checkbox" id="soundToggle" ${this.settings.sound.enabled ? 'checked' : ''}>
                                    <span class="slider round"></span>
                                </label>
                                <span>Enable Sound Effects</span>
                                <button class="test-btn" data-test="sound">🔊 Test</button>
                            </div>
                            <div class="setting-item">
                                <label>Volume: <span id="volumeValue">${Math.round(this.settings.sound.volume * 100)}%</span></label>
                                <input type="range" id="volumeSlider" min="0" max="1" step="0.01" value="${this.settings.sound.volume}">
                            </div>
                        </div>
                        
                        <!-- Voice Settings -->
                        <div class="settings-section">
                            <h3><i class="fas fa-microphone-alt"></i> Voice Assistant</h3>
                            <div class="setting-item">
                                <label class="switch">
                                    <input type="checkbox" id="voiceToggle" ${this.settings.voice.enabled ? 'checked' : ''}>
                                    <span class="slider round"></span>
                                </label>
                                <span>Enable Voice Feedback</span>
                                <button class="test-btn" data-test="voice">🎤 Test</button>
                            </div>
                            <div class="setting-item">
                                <label>Speed: <span id="rateValue">${this.settings.voice.rate}</span></label>
                                <input type="range" id="rateSlider" min="0.5" max="2" step="0.1" value="${this.settings.voice.rate}">
                            </div>
                            <div class="setting-item">
                                <label>Pitch: <span id="pitchValue">${this.settings.voice.pitch}</span></label>
                                <input type="range" id="pitchSlider" min="0.5" max="2" step="0.1" value="${this.settings.voice.pitch}">
                            </div>
                        </div>
                        
                        <!-- Haptics Settings -->
                        <div class="settings-section">
                            <h3><i class="fas fa-hand-peace"></i> Haptics (Vibration)</h3>
                            <div class="setting-item">
                                <label class="switch">
                                    <input type="checkbox" id="hapticsToggle" ${this.settings.haptics.enabled ? 'checked' : ''}>
                                    <span class="slider round"></span>
                                </label>
                                <span>Enable Haptic Feedback</span>
                                <button class="test-btn" data-test="haptics">📳 Test</button>
                            </div>
                            <div class="setting-item">
                                <label>Intensity: <span id="intensityValue">${Math.round(this.settings.haptics.intensity * 100)}%</span></label>
                                <input type="range" id="intensitySlider" min="0" max="1" step="0.1" value="${this.settings.haptics.intensity}">
                            </div>
                        </div>
                        
                        <!-- Tutorial - Redirects to standalone page -->
                        <div class="settings-section">
                            <h3><i class="fas fa-graduation-cap"></i> Tutorial</h3>
                            <div class="setting-item">
                                <button id="startTutorialBtn" class="btn btn-primary">
                                    <i class="fas fa-play"></i> Start Tutorial
                                </button>
                                <button id="resetTutorialBtn" class="btn btn-outline">
                                    <i class="fas fa-sync"></i> Reset Tutorial
                                </button>
                            </div>
                        </div>
                        
                        <!-- Calibration -->
                        <div class="settings-section">
                            <h3><i class="fas fa-sliders-h"></i> Calibration</h3>
                            <div class="setting-item">
                                <label>Hand Size:</label>
                                <select id="handSizeSelect">
                                    <option value="small" ${this.settings.calibration.handSize === 'small' ? 'selected' : ''}>Small</option>
                                    <option value="medium" ${this.settings.calibration.handSize === 'medium' ? 'selected' : ''}>Medium</option>
                                    <option value="large" ${this.settings.calibration.handSize === 'large' ? 'selected' : ''}>Large</option>
                                </select>
                            </div>
                            <div class="setting-item">
                                <label>Sensitivity: <span id="sensitivityValue">${Math.round(this.settings.calibration.sensitivity * 100)}%</span></label>
                                <input type="range" id="sensitivitySlider" min="0" max="1" step="0.1" value="${this.settings.calibration.sensitivity}">
                            </div>
                            <div class="setting-item">
                                <button id="calibrateBtn" class="btn btn-primary">
                                    <i class="fas fa-ruler"></i> Start Calibration
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" id="saveSettingsBtn">Save Settings</button>
                        <button class="btn btn-outline" id="closeSettingsBtn">Close</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', settingsHTML);
        this.addSettingsStyles();
        this.bindEvents();
    }

    addSettingsStyles() {
        if (document.getElementById('ux-settings-styles')) return;
        const style = document.createElement('style');
        style.id = 'ux-settings-styles';
        style.textContent = `
            .ux-settings-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                backdrop-filter: blur(8px);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .ux-settings-modal .modal-content {
                max-width: 600px;
                width: 90%;
                max-height: 85vh;
                overflow-y: auto;
                background: var(--bg-card, #1a1a2e);
                border-radius: 20px;
                border: 1px solid var(--border-color, rgba(255,255,255,0.1));
                box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
            }
            .ux-settings-modal .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 24px;
                border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.1));
            }
            .ux-settings-modal .modal-header h2 {
                font-size: 1.5rem;
                margin: 0;
                color: var(--text-primary, white);
            }
            .ux-settings-modal .close-modal {
                background: none;
                border: none;
                font-size: 28px;
                cursor: pointer;
                color: var(--text-secondary, #888);
            }
            .ux-settings-modal .modal-body {
                padding: 24px;
            }
            .ux-settings-modal .modal-footer {
                padding: 16px 24px;
                border-top: 1px solid var(--border-color, rgba(255,255,255,0.1));
                display: flex;
                justify-content: flex-end;
                gap: 12px;
            }
            .settings-section {
                margin-bottom: 25px;
                padding-bottom: 20px;
                border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.1));
            }
            .settings-section:last-child {
                border-bottom: none;
                margin-bottom: 0;
                padding-bottom: 0;
            }
            .settings-section h3 {
                margin-bottom: 15px;
                color: var(--primary, #81ecff);
                font-size: 1.1rem;
            }
            .setting-item {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-bottom: 12px;
                flex-wrap: wrap;
            }
            .setting-item label {
                min-width: 80px;
                color: var(--text-secondary, #aaa);
            }
            .switch {
                position: relative;
                display: inline-block;
                width: 50px;
                height: 24px;
            }
            .switch input {
                opacity: 0;
                width: 0;
                height: 0;
            }
            .slider {
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: #ccc;
                transition: 0.3s;
                border-radius: 24px;
            }
            .slider:before {
                position: absolute;
                content: "";
                height: 18px;
                width: 18px;
                left: 3px;
                bottom: 3px;
                background-color: white;
                transition: 0.3s;
                border-radius: 50%;
            }
            input:checked + .slider {
                background: var(--gradient, linear-gradient(135deg, #667eea 0%, #764ba2 100%));
            }
            input:checked + .slider:before {
                transform: translateX(26px);
            }
            .test-btn {
                padding: 5px 12px;
                background: var(--bg-secondary, rgba(255,255,255,0.05));
                border: 1px solid var(--border-color, rgba(255,255,255,0.1));
                border-radius: 20px;
                cursor: pointer;
                font-size: 12px;
                color: var(--text-primary, white);
            }
            .test-btn:hover {
                background: var(--gradient, linear-gradient(135deg, #667eea 0%, #764ba2 100%));
                color: white;
            }
            input[type="range"] {
                flex: 1;
                min-width: 200px;
                height: 4px;
                border-radius: 2px;
                background: var(--border-color, rgba(255,255,255,0.2));
            }
            input[type="range"]::-webkit-slider-thumb {
                background: var(--primary, #81ecff);
                border-radius: 50%;
                width: 16px;
                height: 16px;
                cursor: pointer;
            }
            select {
                padding: 8px 12px;
                background: var(--bg-secondary, rgba(255,255,255,0.05));
                border: 1px solid var(--border-color, rgba(255,255,255,0.1));
                border-radius: 8px;
                color: var(--text-primary, white);
            }
            .calibration-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.9);
                z-index: 10001;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .calibration-box {
                background: var(--bg-card, #1a1a2e);
                padding: 30px;
                border-radius: 20px;
                text-align: center;
                max-width: 500px;
                width: 90%;
                border: 1px solid var(--border-color, rgba(255,255,255,0.1));
            }
            .calibration-box h3 {
                color: var(--primary, #81ecff);
                margin-bottom: 16px;
            }
            .notification {
                position: fixed;
                top: 80px;
                right: 20px;
                background: var(--gradient, linear-gradient(135deg, #667eea 0%, #764ba2 100%));
                padding: 12px 20px;
                border-radius: 8px;
                color: white;
                z-index: 10002;
                animation: slideInRight 0.3s ease;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes fadeOut {
                to { opacity: 0; transform: translateY(-10px); }
            }
        `;
        document.head.appendChild(style);
    }

    bindEvents() {
        // Sound
        const soundToggle = document.getElementById('soundToggle');
        if (soundToggle) {
            soundToggle.onchange = (e) => {
                this.settings.sound.enabled = e.target.checked;
                this.saveSettings();
                if (this.settings.sound.enabled) {
                    this.playSound('notification');
                }
            };
        }
        const volumeSlider = document.getElementById('volumeSlider');
        if (volumeSlider) {
            volumeSlider.oninput = (e) => {
                this.settings.sound.volume = parseFloat(e.target.value);
                const volumeValue = document.getElementById('volumeValue');
                if (volumeValue) volumeValue.innerText = Math.round(this.settings.sound.volume * 100) + '%';
                this.saveSettings();
            };
        }

        // Voice
        const voiceToggle = document.getElementById('voiceToggle');
        if (voiceToggle) {
            voiceToggle.onchange = (e) => {
                this.settings.voice.enabled = e.target.checked;
                this.saveSettings();
                if (this.settings.voice.enabled) {
                    this.speak('Voice feedback enabled');
                }
            };
        }
        const rateSlider = document.getElementById('rateSlider');
        if (rateSlider) {
            rateSlider.oninput = (e) => {
                this.settings.voice.rate = parseFloat(e.target.value);
                const rateValue = document.getElementById('rateValue');
                if (rateValue) rateValue.innerText = this.settings.voice.rate;
                this.saveSettings();
            };
        }
        const pitchSlider = document.getElementById('pitchSlider');
        if (pitchSlider) {
            pitchSlider.oninput = (e) => {
                this.settings.voice.pitch = parseFloat(e.target.value);
                const pitchValue = document.getElementById('pitchValue');
                if (pitchValue) pitchValue.innerText = this.settings.voice.pitch;
                this.saveSettings();
            };
        }

        // Haptics
        const hapticsToggle = document.getElementById('hapticsToggle');
        if (hapticsToggle) {
            hapticsToggle.onchange = (e) => {
                this.settings.haptics.enabled = e.target.checked;
                this.saveSettings();
                if (this.settings.haptics.enabled) {
                    this.vibrate(50);
                }
            };
        }
        const intensitySlider = document.getElementById('intensitySlider');
        if (intensitySlider) {
            intensitySlider.oninput = (e) => {
                this.settings.haptics.intensity = parseFloat(e.target.value);
                const intensityValue = document.getElementById('intensityValue');
                if (intensityValue) intensityValue.innerText = Math.round(this.settings.haptics.intensity * 100) + '%';
                this.saveSettings();
            };
        }

        // Test buttons
        document.querySelectorAll('[data-test="sound"]').forEach(btn => {
            btn.onclick = () => this.playSound('click');
        });
        document.querySelectorAll('[data-test="voice"]').forEach(btn => {
            btn.onclick = () => this.speak('This is a voice test. Can you hear me clearly?');
        });
        document.querySelectorAll('[data-test="haptics"]').forEach(btn => {
            btn.onclick = () => this.vibrate([50, 100, 50]);
        });

        // Tutorial - Redirect to standalone page
        const startTutorialBtn = document.getElementById('startTutorialBtn');
        if (startTutorialBtn) {
            startTutorialBtn.onclick = () => {
                window.location.href = '/tutorial';
            };
        }
        const resetTutorialBtn = document.getElementById('resetTutorialBtn');
        if (resetTutorialBtn) {
            resetTutorialBtn.onclick = () => {
                if (confirm('Reset tutorial progress? You will need to complete the tutorial again.')) {
                    this.settings.tutorial.completed = false;
                    this.settings.tutorial.currentStep = 0;
                    this.saveSettings();
                    localStorage.removeItem('tutorial_completed');
                    window.location.href = '/tutorial';
                }
            };
        }

        // Calibration
        const handSizeSelect = document.getElementById('handSizeSelect');
        if (handSizeSelect) {
            handSizeSelect.onchange = (e) => {
                this.settings.calibration.handSize = e.target.value;
                this.saveSettings();
            };
        }
        const sensitivitySlider = document.getElementById('sensitivitySlider');
        if (sensitivitySlider) {
            sensitivitySlider.oninput = (e) => {
                this.settings.calibration.sensitivity = parseFloat(e.target.value);
                const sensitivityValue = document.getElementById('sensitivityValue');
                if (sensitivityValue) sensitivityValue.innerText = Math.round(this.settings.calibration.sensitivity * 100) + '%';
                this.saveSettings();
            };
        }
        const calibrateBtn = document.getElementById('calibrateBtn');
        if (calibrateBtn) calibrateBtn.onclick = () => this.startCalibration();

        // Modal controls
        const closeModalBtn = document.querySelector('#uxSettingsModal .close-modal');
        if (closeModalBtn) closeModalBtn.onclick = () => this.closeModal();
        const closeSettingsBtn = document.getElementById('closeSettingsBtn');
        if (closeSettingsBtn) closeSettingsBtn.onclick = () => this.closeModal();
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.onclick = () => {
                this.saveSettings();
                this.playSound('success');
                this.speak('Settings saved');
                this.closeModal();
            };
        }

        // Close on outside click
        const modal = document.getElementById('uxSettingsModal');
        if (modal) {
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            };
        }
    }

    setupEventListeners() {
        if (window.socket) {
            window.socket.on('gesture_update', (data) => {
                this.onGestureDetected(data);
            });
        }
        this.addSettingsButton();
    }

    addSettingsButton() {
        if (document.getElementById('uxSettingsNavBtn')) return;
        const settingsBtn = document.createElement('button');
        settingsBtn.id = 'uxSettingsNavBtn';
        settingsBtn.className = 'btn btn-outline';
        settingsBtn.innerHTML = '<i class="fas fa-sliders-h"></i> UX Settings';
        settingsBtn.onclick = () => this.openModal();
        const navLinks = document.querySelector('.nav-links');
        if (navLinks) {
            navLinks.appendChild(settingsBtn);
        }
    }

    onGestureDetected(data) {
        if (data.gesture && data.gesture !== 'UNKNOWN') {
            this.playSound('gesture');
            if (this.settings.voice.enabled && data.confidence > 0.8) {
                if (data.gesture === 'PINCH') {
                    this.speak('Click', true);
                } else if (data.gesture === 'PEACE') {
                    this.speak('Right click', true);
                } else if (data.gesture === 'ZOOM') {
                    this.speak('Zoom', true);
                } else if (data.gesture === 'SCROLL') {
                    this.speak('Scroll', true);
                }
            }
            if (data.gesture === 'PINCH') {
                this.vibrate('click');
            } else if (data.gesture === 'PEACE') {
                this.vibrate('gesture');
            } else if (data.confidence > 0.9) {
                this.vibrate(20);
            }
        }
    }

    startCalibration() {
        this.showCalibrationOverlay();
    }

    showCalibrationOverlay() {
        const existing = document.querySelector('.calibration-overlay');
        if (existing) existing.remove();
        const overlay = document.createElement('div');
        overlay.className = 'calibration-overlay';
        overlay.innerHTML = `
            <div class="calibration-box">
                <h3><i class="fas fa-ruler"></i> Hand Calibration</h3>
                <p>Please show your open palm to the camera and hold still for 3 seconds...</p>
                <div style="width: 100%; height: 10px; background: #333; border-radius: 5px; margin: 20px 0;">
                    <div id="calibrationFill" style="width: 0%; height: 100%; background: var(--gradient, linear-gradient(135deg, #667eea 0%, #764ba2 100%)); border-radius: 5px; transition: width 0.1s linear;"></div>
                </div>
                <div id="calibrationStatus">Preparing...</div>
                <button id="cancelCalibration" class="btn btn-outline" style="margin-top: 20px;">Cancel</button>
            </div>
        `;
        document.body.appendChild(overlay);
        let startTime = null;
        let calibrationInterval = null;
        const updateCalibration = () => {
            if (!startTime) startTime = Date.now();
            const elapsed = (Date.now() - startTime) / 1000;
            const progress = Math.min(100, (elapsed / 3) * 100);
            const fill = document.getElementById('calibrationFill');
            const status = document.getElementById('calibrationStatus');
            if (fill) fill.style.width = `${progress}%`;
            if (status) status.innerHTML = `Calibrating... ${Math.round(progress)}%`;
            if (elapsed >= 3) {
                clearInterval(calibrationInterval);
                this.completeCalibration(overlay);
            }
        };
        calibrationInterval = setInterval(updateCalibration, 100);
        const cancelBtn = document.getElementById('cancelCalibration');
        if (cancelBtn) {
            cancelBtn.onclick = () => {
                clearInterval(calibrationInterval);
                overlay.remove();
                this.showNotification('Calibration cancelled');
            };
        }
    }

    completeCalibration(overlay) {
        this.settings.calibration.completed = true;
        this.saveSettings();
        overlay.innerHTML = `
            <div class="calibration-box">
                <h3><i class="fas fa-check-circle"></i> Calibration Complete!</h3>
                <p>Your hand has been calibrated successfully.</p>
                <p>Hand Size: ${this.settings.calibration.handSize}</p>
                <p>Sensitivity: ${Math.round(this.settings.calibration.sensitivity * 100)}%</p>
                <button id="closeCalibration" class="btn btn-primary" style="margin-top: 20px;">Start Using</button>
            </div>
        `;
        const closeBtn = document.getElementById('closeCalibration');
        if (closeBtn) {
            closeBtn.onclick = () => {
                overlay.remove();
                this.playSound('success');
                if (this.settings.voice.enabled) {
                    this.speak('Calibration complete. You can now use gesture control.');
                }
            };
        }
        this.playSound('success');
        this.vibrate('success');
    }

    openModal() {
        const modal = document.getElementById('uxSettingsModal');
        if (modal) modal.style.display = 'flex';
    }

    closeModal() {
        const modal = document.getElementById('uxSettingsModal');
        if (modal) modal.style.display = 'none';
    }

    updateUI() {
        const soundToggle = document.getElementById('soundToggle');
        if (soundToggle) soundToggle.checked = this.settings.sound.enabled;
        const voiceToggle = document.getElementById('voiceToggle');
        if (voiceToggle) voiceToggle.checked = this.settings.voice.enabled;
        const hapticsToggle = document.getElementById('hapticsToggle');
        if (hapticsToggle) hapticsToggle.checked = this.settings.haptics.enabled;
        const volumeSlider = document.getElementById('volumeSlider');
        if (volumeSlider) volumeSlider.value = this.settings.sound.volume;
        const volumeValue = document.getElementById('volumeValue');
        if (volumeValue) volumeValue.innerText = Math.round(this.settings.sound.volume * 100) + '%';
        const rateSlider = document.getElementById('rateSlider');
        if (rateSlider) rateSlider.value = this.settings.voice.rate;
        const rateValue = document.getElementById('rateValue');
        if (rateValue) rateValue.innerText = this.settings.voice.rate;
        const pitchSlider = document.getElementById('pitchSlider');
        if (pitchSlider) pitchSlider.value = this.settings.voice.pitch;
        const pitchValue = document.getElementById('pitchValue');
        if (pitchValue) pitchValue.innerText = this.settings.voice.pitch;
        const intensitySlider = document.getElementById('intensitySlider');
        if (intensitySlider) intensitySlider.value = this.settings.haptics.intensity;
        const intensityValue = document.getElementById('intensityValue');
        if (intensityValue) intensityValue.innerText = Math.round(this.settings.haptics.intensity * 100) + '%';
        const handSizeSelect = document.getElementById('handSizeSelect');
        if (handSizeSelect) handSizeSelect.value = this.settings.calibration.handSize;
        const sensitivitySlider = document.getElementById('sensitivitySlider');
        if (sensitivitySlider) sensitivitySlider.value = this.settings.calibration.sensitivity;
        const sensitivityValue = document.getElementById('sensitivityValue');
        if (sensitivityValue) sensitivityValue.innerText = Math.round(this.settings.calibration.sensitivity * 100) + '%';
    }

    showNotification(message) {
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    checkFirstTimeUser() {
        if (!localStorage.getItem('ux_settings')) {
            setTimeout(() => {
                this.showNotification('👋 Welcome! Click the UX Settings button to customize sound, voice, and haptics.');
            }, 1000);
            // No auto-start tutorial - user must click button
        }
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.uxSettings = new UXSettingsManager();
    });
} else {
    window.uxSettings = new UXSettingsManager();
}