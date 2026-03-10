/* Coffee RPG - Client-side game logic */

(function () {
    'use strict';

    // --- State ---
    let socket = null;
    let myId = null;
    let roomCode = null;
    let currentState = null;
    let isHost = false;

    // --- DOM refs ---
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const screens = {
        title: $('#screen-title'),
        lobby: $('#screen-lobby'),
        game: $('#screen-game'),
        end: $('#screen-end'),
    };

    // --- Helpers ---
    function showScreen(name) {
        Object.values(screens).forEach(s => s.classList.remove('active'));
        screens[name].classList.add('active');
    }

    function toast(msg, type = 'info') {
        const container = $('#toast-container');
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    function saveSession() {
        if (myId && roomCode) {
            sessionStorage.setItem('coffee_rpg_player', myId);
            sessionStorage.setItem('coffee_rpg_room', roomCode);
        }
    }

    function clearSession() {
        sessionStorage.removeItem('coffee_rpg_player');
        sessionStorage.removeItem('coffee_rpg_room');
    }

    const dieFaces = ['', '\u2680', '\u2681', '\u2682', '\u2683', '\u2684', '\u2685'];

    // --- Socket Setup ---
    function initSocket() {
        socket = io();

        socket.on('connect', () => {
            // Try reconnect
            const savedId = sessionStorage.getItem('coffee_rpg_player');
            const savedRoom = sessionStorage.getItem('coffee_rpg_room');
            if (savedId && savedRoom && !myId) {
                socket.emit('reconnect_game', { player_id: savedId, room_code: savedRoom });
            }
        });

        socket.on('error', (data) => {
            toast(data.message, 'error');
        });

        socket.on('game_created', (data) => {
            myId = data.player_id;
            roomCode = data.room_code;
            isHost = true;
            saveSession();
            $('#lobby-room-code').textContent = roomCode;
            showScreen('lobby');
            updateLobby(data.state);
        });

        socket.on('game_joined', (data) => {
            myId = data.player_id;
            roomCode = data.room_code;
            isHost = false;
            saveSession();
            $('#lobby-room-code').textContent = roomCode;
            showScreen('lobby');
        });

        socket.on('reconnected', (data) => {
            myId = data.player_id;
            toast('Reconnected!');
        });

        socket.on('game_state', (data) => {
            currentState = data.state;
            myId = data.your_id;
            // Find if we're host
            const me = currentState.players.find(p => p.id === myId);
            if (me) isHost = me.is_host;
            handleStateUpdate();
        });

        socket.on('sugar_used', (data) => {
            toast(`${data.by} used Sugar! (${data.sugar_remaining} remaining)`, 'info');
        });

        socket.on('x_card_activated', () => {
            $('#x-card-overlay').style.display = 'flex';
            if (currentState && currentState.current_narrator_id === myId) {
                $('#btn-clear-x-card').style.display = 'inline-block';
            } else {
                $('#btn-clear-x-card').style.display = 'none';
            }
        });
    }

    // --- State Update Handler ---
    function handleStateUpdate() {
        const s = currentState;
        if (!s) return;

        switch (s.phase) {
            case 'lobby':
                showScreen('lobby');
                updateLobby(s);
                break;
            case 'brew':
            case 'pour':
                showScreen('game');
                updateGame(s);
                break;
            case 'ended':
                showScreen('end');
                updateEnd(s);
                break;
        }
    }

    // --- Lobby ---
    function updateLobby(s) {
        const list = $('#lobby-players');
        list.innerHTML = '';
        (s.players || []).forEach(p => {
            const el = document.createElement('div');
            el.className = 'player-item' + (p.id === myId ? ' current' : '');
            el.innerHTML = `
                <span class="player-dot ${p.connected ? '' : 'disconnected'}"></span>
                <span class="player-name">${esc(p.name)}</span>
                ${p.is_host ? '<span class="player-host">Host</span>' : ''}
                ${p.id === myId ? '<span class="player-host">You</span>' : ''}
            `;
            list.appendChild(el);
        });

        if (isHost) {
            $('#host-setup').style.display = 'block';
            $('#guest-waiting').style.display = 'none';
        } else {
            $('#host-setup').style.display = 'none';
            $('#guest-waiting').style.display = 'block';
        }
    }

    // --- Game ---
    function updateGame(s) {
        updateSidebar(s);
        updateStoryLog(s);
        updatePhasePanel(s);
    }

    function updateSidebar(s) {
        // Players
        const list = $('#game-players');
        list.innerHTML = '';
        (s.players || []).forEach(p => {
            const el = document.createElement('div');
            const isNarrator = p.id === s.current_narrator_id;
            el.className = 'player-item' + (p.id === myId ? ' current' : '');
            el.innerHTML = `
                <span class="player-dot ${p.connected ? '' : 'disconnected'}"></span>
                <span class="player-name">${esc(p.name)}</span>
                ${isNarrator ? '<span class="player-narrator">Narrator</span>' : ''}
            `;
            list.appendChild(el);
        });

        // Resources
        $('#sugar-count').textContent = s.sugar;
        const maxSips = s.max_sips ? `${s.sip_count} / ${s.max_sips}` : s.sip_count;
        $('#sip-counter').textContent = maxSips;

        // Style
        const styles = { black: 'Black', milk: 'With Milk', milk_and_sugar: 'With Milk & Sugar' };
        $('#coffee-style-display').textContent = styles[s.coffee_style] || '';

        // Side characters
        const charList = $('#side-characters');
        if (s.side_characters.length === 0) {
            charList.innerHTML = '<p class="empty-note">None yet</p>';
        } else {
            charList.innerHTML = '';
            s.side_characters.forEach(sc => {
                const el = document.createElement('div');
                el.className = `side-char-item ${sc.positive ? 'positive' : 'negative'}`;
                el.innerHTML = `
                    <div class="char-name">${esc(sc.name)}</div>
                    <div class="char-desc">${esc(sc.description)}</div>
                `;
                charList.appendChild(el);
            });
        }

        // End game button (host only)
        $('#btn-end-game').style.display = isHost ? 'inline-block' : 'none';
    }

    function updateStoryLog(s) {
        const log = $('#story-log');
        log.innerHTML = '';
        (s.past_sips || []).forEach(sip => {
            log.appendChild(createSipEntry(sip));
        });
        // Scroll to bottom
        log.scrollTop = log.scrollHeight;
    }

    function createSipEntry(sip) {
        const entry = document.createElement('div');
        entry.className = 'story-entry';

        let metaHtml = '';
        if (sip.die_result != null) {
            const favClass = sip.favorable ? 'favorable' : 'unfavorable';
            const favText = sip.favorable ? 'Favorable' : 'Unfavorable';
            metaHtml += `<span class="die-badge ${favClass}">${dieFaces[sip.die_result]} ${favText}</span>`;
        }
        if (sip.sugar_used) {
            metaHtml += '<span class="sugar-badge">Sugar used</span>';
        }
        if (sip.side_character) {
            const charClass = sip.side_character.positive ? 'positive' : 'negative';
            metaHtml += `<span class="char-badge ${charClass}">${esc(sip.side_character.name)}</span>`;
        }

        let html = '';
        // Brew part
        if (sip.brew_narration) {
            html += `
                <div class="story-entry-header">
                    <span class="story-entry-phase brew">Brew &mdash; Sip ${sip.number}</span>
                    <span class="story-entry-narrator">${esc(sip.narrator_name)}</span>
                </div>
                <div class="story-entry-text">${esc(sip.brew_narration)}</div>
                ${metaHtml ? `<div class="story-entry-meta">${metaHtml}</div>` : ''}
            `;
        }
        // Pour part
        if (sip.pour_narration) {
            html += `
                <div class="story-entry-header" style="margin-top:12px;">
                    <span class="story-entry-phase pour">Pour</span>
                </div>
                <div class="story-entry-text">${esc(sip.pour_narration)}</div>
            `;
        }
        if (sip.pour_question) {
            html += `<div class="story-entry-question">${esc(sip.pour_question)}</div>`;
        }

        entry.innerHTML = html;
        return entry;
    }

    function updatePhasePanel(s) {
        const brewPanel = $('#phase-brew');
        const pourPanel = $('#phase-pour');
        brewPanel.style.display = 'none';
        pourPanel.style.display = 'none';

        if (s.phase === 'brew') {
            brewPanel.style.display = 'block';
            updateBrewPanel(s);
        } else if (s.phase === 'pour') {
            pourPanel.style.display = 'block';
            updatePourPanel(s);
        }
    }

    function updateBrewPanel(s) {
        const sip = s.current_sip;
        const isMyTurn = s.current_narrator_id === myId;
        const narrator = s.players.find(p => p.id === s.current_narrator_id);
        const narratorName = narrator ? narrator.name : '?';

        $('#brew-narrator').textContent = isMyTurn ? 'Your turn' : `${narratorName}'s turn`;

        // Previous question
        const prevQ = $('#brew-previous-question');
        const lastSip = s.past_sips.length > 0 ? s.past_sips[s.past_sips.length - 1] : null;
        if (lastSip && lastSip.pour_question) {
            prevQ.style.display = 'block';
            prevQ.innerHTML = `<strong>Previous question:</strong> ${esc(lastSip.pour_question)}`;
        } else if (s.sip_count === 1) {
            prevQ.style.display = 'block';
            prevQ.innerHTML = '<em>First Brew — narrate a situation involving the protagonist and resolve it immediately.</em>';
        } else {
            prevQ.style.display = 'none';
        }

        // Cup and roll
        const cupEl = $('#brew-cup');
        const resultEl = $('#brew-result');
        const waitingEl = $('#brew-waiting');

        if (isMyTurn) {
            waitingEl.style.display = 'none';

            if (s.brew_phase === 'rolling') {
                cupEl.style.display = 'flex';
                resultEl.style.display = 'none';
                $('#btn-roll').style.display = 'inline-block';
                $('#cup-contents').innerHTML = '<span class="cup-prompt">Roll the die</span>';
            } else if (s.brew_phase === 'narrating') {
                cupEl.style.display = 'flex';
                resultEl.style.display = 'block';
                $('#btn-roll').style.display = 'none';

                // Show die result to narrator
                const die = sip.die_result;
                const fav = sip.favorable;
                $('#cup-contents').innerHTML = `<span class="die-face">${dieFaces[die]}</span>`;
                const favClass = fav ? 'favorable' : 'unfavorable';
                const favText = fav ? 'Favorable' : 'Unfavorable';
                $('#die-result-display').className = `die-result ${favClass}`;
                $('#die-result-display').innerHTML = `<span class="die-number">${die}</span>`;
                $('#brew-outcome').className = `outcome-badge ${favClass}`;
                $('#brew-outcome').textContent = `${favText} outcome${sip.sugar_used ? ' (Sugar inverted!)' : ''}`;

                // Sugar button (anyone can use, but not narrator? Actually anyone can)
                if (s.sugar > 0 && !sip.sugar_used) {
                    $('#sugar-action').style.display = 'block';
                } else {
                    $('#sugar-action').style.display = 'none';
                }

                // Narration textarea
                $('#brew-narrate').style.display = 'block';
            } else if (s.brew_phase === 'revealed') {
                // Shouldn't normally be here for brew, transitions to pour
                cupEl.style.display = 'none';
                resultEl.style.display = 'none';
            }
        } else {
            // Not our turn
            cupEl.style.display = 'none';
            resultEl.style.display = 'none';

            if (s.brew_phase === 'rolling') {
                waitingEl.style.display = 'block';
                $('#brew-waiting-text').textContent = `${narratorName} is rolling the die under the cup...`;
            } else if (s.brew_phase === 'narrating') {
                waitingEl.style.display = 'block';
                $('#brew-waiting-text').textContent = `${narratorName} is writing the Brew narration...`;

                // Others can still use sugar
                if (s.sugar > 0 && !sip.sugar_used) {
                    resultEl.style.display = 'block';
                    $('#die-result-display').innerHTML = '<span class="die-number">?</span>';
                    $('#die-result-display').className = 'die-result';
                    $('#brew-outcome').textContent = 'Die is hidden under the cup';
                    $('#brew-outcome').className = 'outcome-badge';
                    $('#sugar-action').style.display = 'block';
                    $('#brew-narrate').style.display = 'none';
                } else {
                    resultEl.style.display = 'none';
                }
            }
        }
    }

    function updatePourPanel(s) {
        const isMyTurn = s.current_narrator_id === myId;
        const narrator = s.players.find(p => p.id === s.current_narrator_id);
        const narratorName = narrator ? narrator.name : '?';

        $('#pour-narrator').textContent = isMyTurn ? 'Your turn' : `${narratorName}'s turn`;

        if (isMyTurn) {
            $('#pour-form').style.display = 'block';
            $('#pour-waiting').style.display = 'none';
            // Reset fields
            if (!$('#pour-text').value) {
                $('#pour-text').value = '';
                $('#pour-question').value = '';
            }
        } else {
            $('#pour-form').style.display = 'none';
            $('#pour-waiting').style.display = 'block';
            $('#pour-waiting-text').textContent = `${narratorName} is writing the Pour narration...`;
        }
    }

    function updateEnd(s) {
        const log = $('#end-story-log');
        log.innerHTML = '';
        (s.past_sips || []).forEach(sip => {
            log.appendChild(createSipEntry(sip));
        });
    }

    // --- Escape HTML ---
    function esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // --- Event Bindings ---
    function bindEvents() {
        // Title screen
        $('#btn-create').addEventListener('click', () => {
            const name = $('#player-name').value.trim();
            if (!name) { toast('Please enter your name.', 'error'); return; }
            socket.emit('create_game', { name });
        });

        $('#btn-join').addEventListener('click', () => {
            const name = $('#player-name').value.trim();
            const code = $('#join-code').value.trim();
            if (!name) { toast('Please enter your name.', 'error'); return; }
            if (!code) { toast('Please enter a room code.', 'error'); return; }
            socket.emit('join_game', { name, room_code: code });
        });

        // Enter key on inputs
        $('#player-name').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const code = $('#join-code').value.trim();
                if (code) $('#btn-join').click();
                else $('#btn-create').click();
            }
        });
        $('#join-code').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') $('#btn-join').click();
        });

        // Lobby
        $('#btn-copy-code').addEventListener('click', () => {
            navigator.clipboard.writeText(roomCode).then(() => toast('Room code copied!'));
        });
        $('#btn-copy-link').addEventListener('click', () => {
            const link = `${window.location.origin}/join/${roomCode}`;
            navigator.clipboard.writeText(link).then(() => toast('Invite link copied!'));
        });
        $('#btn-start').addEventListener('click', () => {
            const style = document.querySelector('input[name="coffee-style"]:checked').value;
            const length = document.querySelector('input[name="game-length"]:checked').value;
            socket.emit('start_game', { coffee_style: style, game_length: length });
        });

        // Brew
        $('#btn-roll').addEventListener('click', () => {
            socket.emit('roll_die');
        });
        $('#btn-sugar').addEventListener('click', () => {
            socket.emit('use_sugar');
        });
        $('#btn-submit-brew').addEventListener('click', () => {
            const text = $('#brew-text').value.trim();
            if (!text) { toast('Please write your narration.', 'error'); return; }
            socket.emit('submit_brew', { narration: text });
            $('#brew-text').value = '';
        });

        // Pour
        $$('input[name="coffee-action"]').forEach(radio => {
            radio.addEventListener('change', () => {
                const val = document.querySelector('input[name="coffee-action"]:checked').value;
                $('#side-char-fields').style.display = val ? 'flex' : 'none';
            });
        });
        $('#btn-submit-pour').addEventListener('click', () => {
            const text = $('#pour-text').value.trim();
            const question = $('#pour-question').value.trim();
            if (!text) { toast('Please write your narration.', 'error'); return; }
            if (!question) { toast('Please end with a question.', 'error'); return; }
            const coffeeAction = document.querySelector('input[name="coffee-action"]:checked');
            const action = coffeeAction ? coffeeAction.value : '';
            const data = {
                narration: text,
                question: question,
            };
            if (action) {
                data.coffee_action = action;
                data.side_char_name = $('#side-char-name').value.trim();
                data.side_char_desc = $('#side-char-desc').value.trim();
            }
            socket.emit('submit_pour', data);
            // Reset form
            $('#pour-text').value = '';
            $('#pour-question').value = '';
            $('#side-char-name').value = '';
            $('#side-char-desc').value = '';
            if (coffeeAction) coffeeAction.checked = false;
            // Select the "no side character" option
            const noChar = document.querySelector('input[name="coffee-action"][value=""]');
            if (noChar) noChar.checked = true;
            $('#side-char-fields').style.display = 'none';
        });

        // X-Card
        $('#btn-x-card').addEventListener('click', () => {
            socket.emit('x_card');
        });
        $('#btn-clear-x-card').addEventListener('click', () => {
            socket.emit('clear_x_card');
            $('#x-card-overlay').style.display = 'none';
        });

        // End game
        $('#btn-end-game').addEventListener('click', () => {
            if (confirm('End the game for everyone?')) {
                socket.emit('end_game');
            }
        });

        // New game
        $('#btn-new-game').addEventListener('click', () => {
            clearSession();
            myId = null;
            roomCode = null;
            currentState = null;
            isHost = false;
            showScreen('title');
        });
    }

    // --- Init ---
    document.addEventListener('DOMContentLoaded', () => {
        bindEvents();
        initSocket();

        // Auto-fill join code from URL if present
        const joinCodeEl = $('#join-code');
        if (joinCodeEl.value) {
            // Code was set by the template
        }
    });
})();
