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

    messageInput.focus();

    chatForm.addEventListener('submit', handleSubmit);
    newChatBtn.addEventListener('click', resetChat);

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

            if (isFirstMessage) {
                response = await startChat(message);
                if (!response.error) {
                    userId = response.user_id;
                    chatId = response.chat_id;
                    isFirstMessage = false;
                    updateStatus('Session active');
                }
            } else {
                response = await sendMessage(message);
            }

            hideTypingIndicator();

            if (response.error) {
                addMessage('Warning: ' + response.error, 'bot');
                updateStatus('Waiting for a valid prompt');
            } else {
                addMessage(response.response, 'bot');
                updateStatus('Ready for your next question');
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
        chatMessages.innerHTML = welcomeMarkup;
        messageInput.value = '';
        setProcessing(false);
        updateStatus('Ready for your first prompt');
        messageInput.focus();
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
