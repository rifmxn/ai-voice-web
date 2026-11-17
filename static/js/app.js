/* ====================================================================
   app.js - Logik Interaksi Web Ejen AI Suara & Teks
   ==================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chatContainer');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const autoVoiceToggle = document.getElementById('autoVoiceToggle');
    const promptChips = document.querySelectorAll('.prompt-chip');

    let currentAudio = null;
    let currentPlayBtn = null;

    // Format masa ringkas (contoh: 10:45 AM)
    function getCurrentTimeString() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Skrol ke bahagian bawah chat
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Format teks markdown ringkas (bold, italics, bullets, linebreaks)
    function formatText(text) {
        if (!text) return "";
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/_(.*?)_/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">$1</code>');

        // Line breaks
        const lines = formatted.split('\n');
        let html = '';
        let inList = false;

        for (let line of lines) {
            line = line.trim();
            if (line.startsWith('• ') || line.startsWith('- ')) {
                if (!inList) {
                    html += '<ul style="margin: 6px 0 6px 20px;">';
                    inList = true;
                }
                html += `<li>${line.substring(2)}</li>`;
            } else {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                if (line) {
                    html += `<p style="margin-bottom: 6px;">${line}</p>`;
                }
            }
        }
        if (inList) html += '</ul>';
        return html;
    }

    // Tambah mesej pengguna ke antaramuka
    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user-message';
        msgDiv.innerHTML = `
            <div class="msg-avatar">👤</div>
            <div class="msg-content">
                <div class="msg-bubble">
                    <p>${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>
                </div>
                <span class="msg-time">${getCurrentTimeString()}</span>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    // Tambah penunjuk visual sedang menaip
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai-message';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-content">
                <div class="msg-bubble typing-bubble">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;
        chatContainer.appendChild(typingDiv);
        scrollToBottom();
        return typingDiv;
    }

    // Tambah mesej AI bersama pemain audio
    function appendAIMessage(text, audioUrl) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai-message';

        let audioPlayerHtml = '';
        if (audioUrl) {
            audioPlayerHtml = `
                <div class="audio-card">
                    <button class="btn-play" data-src="${audioUrl}">▶</button>
                    <div class="audio-info">
                        <span class="audio-label">🔊 Dengar Suara AI</span>
                        <div class="audio-progress-bar">
                            <div class="audio-progress-fill"></div>
                        </div>
                    </div>
                </div>
            `;
        }

        msgDiv.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-content">
                <div class="msg-bubble">
                    ${formatText(text)}
                    ${audioPlayerHtml}
                </div>
                <span class="msg-time">${getCurrentTimeString()}</span>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        scrollToBottom();

        // Hubungkan fungsi pemain audio jika ada audioUrl
        if (audioUrl) {
            const playBtn = msgDiv.querySelector('.btn-play');
            const progressFill = msgDiv.querySelector('.audio-progress-fill');
            setupAudioPlayer(playBtn, progressFill, audioUrl);

            // Auto-play sekiranya suis Auto Suara diaktifkan
            if (autoVoiceToggle.checked) {
                setTimeout(() => {
                    playBtn.click();
                }, 150);
            }
        }
    }

    // Pengurusan Main/Jeda Audio
    function setupAudioPlayer(button, progressFill, audioSrc) {
        const audio = new Audio(audioSrc);

        button.addEventListener('click', () => {
            // Jika ada audio lain yang sedang dimainkan, jedakannya
            if (currentAudio && currentAudio !== audio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
                if (currentPlayBtn) currentPlayBtn.textContent = '▶';
            }

            if (audio.paused) {
                audio.play().then(() => {
                    button.textContent = '⏸';
                    currentAudio = audio;
                    currentPlayBtn = button;
                }).catch(err => {
                    console.warn("Autoplay dihalang oleh pelayar:", err);
                    button.textContent = '▶';
                });
            } else {
                audio.pause();
                button.textContent = '▶';
            }
        });

        audio.addEventListener('timeupdate', () => {
            if (audio.duration) {
                const percent = (audio.currentTime / audio.duration) * 100;
                progressFill.style.width = percent + '%';
            }
        });

        audio.addEventListener('ended', () => {
            button.textContent = '▶';
            progressFill.style.width = '0%';
        });
    }

    // Penghantaran Mesej ke Backend
    async function sendMessage(text) {
        const cleanText = text.trim();
        if (!cleanText) return;

        appendUserMessage(cleanText);
        messageInput.value = '';
        messageInput.disabled = true;
        sendBtn.disabled = true;

        const typingIndicator = showTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: cleanText })
            });

            const data = await response.json();
            typingIndicator.remove();

            if (data.status === 'success') {
                appendAIMessage(data.text, data.audio_url);
            } else {
                appendAIMessage("⚠️ Maaf, berlaku ralat: " + (data.error || "Gagal memproses."), null);
            }
        } catch (error) {
            console.error("Ralat rangkaian:", error);
            typingIndicator.remove();
            appendAIMessage("⚠️ Maaf, tidak dapat berhubung dengan pelayan AI tempatan.", null);
        } finally {
            messageInput.disabled = false;
            sendBtn.disabled = false;
            messageInput.focus();
        }
    }

    // Event Listeners
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage(messageInput.value);
    });

    // Quick Prompt Chips
    promptChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const prompt = chip.getAttribute('data-text');
            if (prompt) {
                sendMessage(prompt);
            }
        });
    });

    // Kosongkan Chat
    clearChatBtn.addEventListener('click', async () => {
        if (!confirm("Adakah anda pasti ingin mengosongkan perbualan ini?")) return;

        try {
            await fetch('/api/clear', { method: 'POST' });
        } catch (e) {
            console.warn(e);
        }

        // Hentikan sebarang audio yang sedang berbunyi
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        chatContainer.innerHTML = `
            <div class="message ai-message">
                <div class="msg-avatar">🤖</div>
                <div class="msg-content">
                    <div class="msg-bubble">
                        <p>🧹 <strong>Perbualan telah dikosongkan.</strong></p>
                        <p>Sedia untuk soalan baharu anda!</p>
                    </div>
                    <span class="msg-time">${getCurrentTimeString()}</span>
                </div>
            </div>
        `;
    });
});
