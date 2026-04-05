/**
 * MarketEye Chat Interface
 * Handles user interactions and API communication
 */

(function() {
    'use strict';

    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const chatStatus = document.getElementById('chat-status');
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const historyList = document.getElementById('history-list');
    const storageKey = 'marketeye-active-chat';

    const welcomeMarkup = `
        <div class="message bot-message">
            <div class="message-content">
                <p>Welcome to MarketEye.</p>
                <p>I'll help you analyze your product idea and generate market research insights.</p>
                <p><strong>Start by describing the product, audience, or problem you want to solve.</strong></p>
                <p><em>Example: I'm building a low-cost smartphone with solar charging for rural markets.</em></p>
            </div>
        </div>
    `;

    let isFirstMessage = true;
    let isProcessing = false;
    let userId = null;
    let chatId = null;
    let currentStatus = null;

    restoreSession();
    loadHistory();
    messageInput.focus();

    chatForm.addEventListener('submit', handleSubmit);
    newChatBtn.addEventListener('click', resetChat);
    exportPdfBtn.addEventListener('click', exportPdf);

    async function handleSubmit(e) {
        e.preventDefault();

        const message = messageInput.value.trim();
        if (!message || isProcessing) return;

        addMessage(message, 'user');
        messageInput.value = '';
        updateStatus('Analyzing your request...');

        setProcessing(true);
        showTypingIndicator();

        try {
            let response;

            const shouldStartFreshChat = isFirstMessage || currentStatus === 'MARKET_RESEARCH_READY';

            if (shouldStartFreshChat) {
                response = await startChat(message);
                if (!response.error) {
                    userId = response.user_id;
                    chatId = response.chat_id;
                    isFirstMessage = false;
                    currentStatus = response.status || null;
                    persistSession();
                    updateStatus('Session active');
                    syncExportAvailability(response.status);
                    loadHistory();
                }
            } else {
                response = await sendMessage(message);
            }

            hideTypingIndicator();

            if (response.error) {
                addMessage('Warning: ' + response.error, 'bot');
                updateStatus('Waiting for a valid prompt');
            } else {
                currentStatus = response.status || null;
                addMessage(response.response, 'bot');
                updateStatus(response.status === 'MARKET_RESEARCH_READY' ? 'Report ready to export' : 'Ready for your next question');
                syncExportAvailability(response.status);
                loadHistory();
            }
        } catch (error) {
            hideTypingIndicator();
            addMessage('Warning: Something went wrong. Please try again.', 'bot');
            updateStatus('Request failed. Try again');
            console.error('Chat error:', error);
        }

        setProcessing(false);
        messageInput.focus();
    }

    async function startChat(message) {
        const response = await fetch('/api/chat/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        return response.json();
    }

    async function sendMessage(message) {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, user_id: userId, chat_id: chatId })
        });
        return response.json();
    }

    function resetChat() {
        userId = null;
        chatId = null;
        isFirstMessage = true;
        currentStatus = null;
        clearSession();
        chatMessages.innerHTML = welcomeMarkup;
        messageInput.value = '';
        setProcessing(false);
        updateStatus('Ready for your first prompt');
        syncExportAvailability();
        loadHistory();
        messageInput.focus();
    }

    function restoreSession() {
        try {
            const raw = localStorage.getItem(storageKey);
            if (!raw) {
                syncExportAvailability();
                return;
            }

            const session = JSON.parse(raw);
            userId = session.user_id || null;
            chatId = session.chat_id || null;
            currentStatus = session.status || null;
            isFirstMessage = !(userId && chatId) || currentStatus === 'MARKET_RESEARCH_READY';
            syncExportAvailability(session.status);

            if (userId && chatId) {
                updateStatus(session.status === 'MARKET_RESEARCH_READY' ? 'Last report ready to export. Send a new idea to start a new chat.' : 'Previous session restored');
            }
        } catch (error) {
            console.warn('Unable to restore session', error);
            currentStatus = null;
            syncExportAvailability();
        }
    }

    function persistSession(status) {
        if (!userId || !chatId) return;

        localStorage.setItem(storageKey, JSON.stringify({
            user_id: userId,
            chat_id: chatId,
            status: status || currentStatus || null
        }));
    }

    function clearSession() {
        localStorage.removeItem(storageKey);
    }

    function syncExportAvailability(status) {
        currentStatus = status || currentStatus || null;
        const isReady = Boolean(userId && chatId && currentStatus === 'MARKET_RESEARCH_READY');
        exportPdfBtn.disabled = !isReady;
        persistSession(currentStatus);
    }

    async function exportPdf() {
        if (!userId || !chatId) return;

        exportPdfBtn.disabled = true;
        updateStatus('Preparing PDF export...');

        try {
            const response = await fetch(`/api/chat/export/${encodeURIComponent(userId)}/${encodeURIComponent(chatId)}`);
            if (!response.ok) {
                const data = await response.json().catch(() => ({ error: 'Export failed.' }));
                throw new Error(data.error || 'Export failed.');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = `${userId}_${chatId}.pdf`;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            window.URL.revokeObjectURL(url);
            updateStatus('PDF exported successfully');
        } catch (error) {
            console.error('PDF export error:', error);
            addMessage(`Warning: ${error.message}`, 'bot');
            updateStatus('PDF export failed');
        } finally {
            syncExportAvailability('MARKET_RESEARCH_READY');
        }
    }

    async function loadHistory() {
        if (!historyList) return;

        try {
            const response = await fetch('/api/chats');
            const data = await response.json();
            const chats = Array.isArray(data.chats) ? data.chats : [];
            renderHistory(chats);
        } catch (error) {
            console.error('History load error:', error);
        }
    }

    function renderHistory(chats) {
        if (!historyList) return;

        const introCard = `
            <article class="insight-card insight-card-active">
                <span class="insight-badge">Live</span>
                <h2>New chat</h2>
                <p>Describe your idea and MarketEye will build the analysis progressively.</p>
            </article>
        `;

        if (!chats.length) {
            historyList.innerHTML = `${introCard}
                <article class="insight-card">
                    <span class="insight-badge">Empty</span>
                    <h2>No saved chats</h2>
                    <p>Your completed and in-progress conversations will appear here.</p>
                </article>`;
            return;
        }

        const items = chats.map((chat) => {
            const activeClass = chat.user_id === userId && chat.chat_id === chatId ? ' insight-card-active' : '';
            const badge = chat.finalized ? 'Ready' : 'Live';
            const updated = formatTimestamp(chat.updated_at);
            return `
                <article class="insight-card history-card${activeClass}" data-user-id="${escapeHtml(chat.user_id)}" data-chat-id="${escapeHtml(chat.chat_id)}">
                    <span class="insight-badge">${badge}</span>
                    <h2 class="history-card-title">${escapeHtml(chat.title || 'Untitled chat')}</h2>
                    <p class="history-card-meta">${escapeHtml((chat.status || '').replaceAll('_', ' ').toLowerCase())}</p>
                    <p class="history-card-meta">${escapeHtml(updated)}</p>
                </article>
            `;
        }).join('');

        historyList.innerHTML = introCard + items;
        historyList.querySelectorAll('.history-card').forEach((card) => {
            card.addEventListener('click', () => {
                const selectedUserId = card.dataset.userId;
                const selectedChatId = card.dataset.chatId;
                if (selectedUserId && selectedChatId) {
                    openSavedChat(selectedUserId, selectedChatId);
                }
            });
        });
    }

    async function openSavedChat(selectedUserId, selectedChatId) {
        updateStatus('Loading saved chat...');
        try {
            const response = await fetch(`/api/chat/${encodeURIComponent(selectedUserId)}/${encodeURIComponent(selectedChatId)}`);
            const chat = await response.json();
            if (!response.ok) {
                throw new Error(chat.error || 'Unable to load chat.');
            }

            userId = chat.user_id || selectedUserId;
            chatId = chat.chat_id || selectedChatId;
            currentStatus = chat.status || null;
            isFirstMessage = !(userId && chatId) || currentStatus === 'MARKET_RESEARCH_READY';
            persistSession(currentStatus);
            syncExportAvailability(currentStatus);
            renderConversation(chat.conversation_history || []);
            updateStatus(currentStatus === 'MARKET_RESEARCH_READY' ? 'Saved report ready to export. Send a new idea to start a new chat.' : 'Saved chat loaded');
            loadHistory();
        } catch (error) {
            console.error('Open chat error:', error);
            addMessage(`Warning: ${error.message}`, 'bot');
            updateStatus('Unable to load saved chat');
        }
    }

    function renderConversation(conversation) {
        if (!Array.isArray(conversation) || !conversation.length) {
            chatMessages.innerHTML = welcomeMarkup;
            return;
        }

        chatMessages.innerHTML = '';
        conversation.forEach((entry) => {
            const sender = entry.role === 'user' ? 'user' : 'bot';
            addMessage(entry.text || '', sender);
        });
    }

    function formatTimestamp(value) {
        if (!value) return 'Unknown date';
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return value;
        return parsed.toLocaleString();
    }

    function escapeHtml(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = formatMessage(content);

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function formatMessage(text) {
        if (!text) return '';

        let formatted = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        formatted = formatted.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        formatted = formatted.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');

        formatted = formatted
            .split('\n\n')
            .map((para) => para.trim())
            .filter(Boolean)
            .map((para) => {
                if (para.startsWith('<h')) return para;
                if (para.startsWith('-') || para.startsWith('*')) {
                    return para.split('\n').map((line) => `<p>${line}</p>`).join('');
                }
                return `<p>${para.replace(/\n/g, '<br>')}</p>`;
            })
            .join('');

        return formatted;
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message bot-message';
        indicator.id = 'typing-indicator';
        indicator.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function setProcessing(state) {
        isProcessing = state;
        sendBtn.disabled = state;
        messageInput.disabled = state;
    }

    function updateStatus(text) {
        if (chatStatus) {
            chatStatus.textContent = text;
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
})();
