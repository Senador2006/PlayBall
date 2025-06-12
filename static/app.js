// Global variables
let currentUser = null;
let authToken = null;
let selectedPlayer = null;
const API_BASE = 'http://localhost:5000';

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('currentUser');
    
    if (token && user) {
        authToken = token;
        currentUser = JSON.parse(user);
        if (currentUser.user_type === 'trainer') {
            showPlayersPage();
        }
    } else {
        showLanding();
    }
});

// Navigation functions
function showLanding() {
    hideAllSections();
    document.getElementById('landing-section').style.display = 'block';
    document.getElementById('nav').style.display = 'none';
}

function showAuth() {
    hideAllSections();
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
}

function showRegister() {
    hideAllSections();
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
}

function showPlayersPage() {
    hideAllSections();
    document.getElementById('players-section').style.display = 'block';
    document.getElementById('nav').style.display = 'block';
    if (currentUser) {
        document.getElementById('trainer-name').textContent = `${currentUser.first_name} ${currentUser.last_name}`;
    }
    loadPlayers();
}

function showAddPlayerPage() {
    hideAllSections();
    document.getElementById('add-player-section').style.display = 'block';
    document.getElementById('nav').style.display = 'block';
}

function showPlayerDetail(player) {
    selectedPlayer = player;
    hideAllSections();
    document.getElementById('player-detail-section').style.display = 'block';
    document.getElementById('nav').style.display = 'block';
    document.getElementById('player-detail-name').innerHTML = `<i class="fas fa-user"></i> ${player.first_name} ${player.last_name}`;
    loadPlayerDetail(player);
    showDetailTab('overview');
}

function hideAllSections() {
    const sections = ['landing-section', 'auth-section', 'players-section', 'add-player-section', 'player-detail-section'];
    sections.forEach(sectionId => {
        document.getElementById(sectionId).style.display = 'none';
    });
}

// Utility functions
function showNotification(message, isError = false) {
    const notification = document.getElementById('notification');
    const text = document.getElementById('notification-text');
    
    text.textContent = message;
    notification.className = `notification show ${isError ? 'error' : ''}`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function makeRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    if (authToken) {
        defaultOptions.headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    return fetch(url, { ...defaultOptions, ...options });
}

// Authentication
async function login(event) {
    event.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const response = await makeRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            currentUser = data.user;
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            showNotification('Login realizado com sucesso!');
            
            if (currentUser.user_type === 'trainer') {
                showPlayersPage();
            } else {
                showNotification('Login de jogadores não disponível nesta versão', true);
                logout();
            }
        } else {
            showNotification(data.message || 'Erro no login', true);
        }
    } catch (error) {
        showNotification('Erro de conexão', true);
        console.error('Login error:', error);
    }
}

async function registerTrainer(event) {
    event.preventDefault();
    
    const firstName = document.getElementById('reg-first-name').value;
    const lastName = document.getElementById('reg-last-name').value;
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirmPassword = document.getElementById('reg-confirm-password').value;
    
    if (password !== confirmPassword) {
        showNotification('As senhas não coincidem', true);
        return;
    }
    
    try {
        const response = await makeRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                first_name: firstName,
                last_name: lastName,
                username,
                email,
                password,
                user_type: 'trainer'
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Conta criada com sucesso! Fazendo login...');
            
            // Auto-login após registro
            setTimeout(() => {
                document.getElementById('login-username').value = username;
                document.getElementById('login-password').value = password;
                const loginEvent = { preventDefault: () => {} };
                login(loginEvent);
            }, 1000);
        } else {
            showNotification(data.message || 'Erro ao criar conta', true);
        }
    } catch (error) {
        showNotification('Erro de conexão', true);
        console.error('Register error:', error);
    }
}

function quickLogin(username, password) {
    document.getElementById('login-username').value = username;
    document.getElementById('login-password').value = password;
    
    const event = { preventDefault: () => {} };
    login(event);
}

function logout() {
    authToken = null;
    currentUser = null;
    selectedPlayer = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    
    showLanding();
    showNotification('Logout realizado com sucesso!');
}

// Detail tabs functions
function showDetailTab(tabName) {
    const tabs = ['overview', 'trainings', 'analytics'];
    tabs.forEach(tab => {
        document.getElementById(`${tab}-tab`).style.display = 'none';
    });
    
    document.querySelectorAll('.detail-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(`${tabName}-tab`).style.display = 'block';
    event.target.classList.add('active');
}

async function loadPlayers() {
    try {
        const response = await makeRequest('/trainer/players');
        const data = await response.json();
        
        if (response.ok) {
            displayPlayers(data.players || []);
        } else {
            showNotification('Erro ao carregar jogadores', true);
            displayPlayers([]);
        }
    } catch (error) {
        showNotification('Erro de conexão', true);
        console.error('Load players error:', error);
        displayPlayers([]);
    }
}

function displayPlayers(players) {
    const container = document.getElementById('players-list');
    const emptyState = document.getElementById('empty-state');
    
    if (!players || players.length === 0) {
        container.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    container.style.display = 'grid';
    emptyState.style.display = 'none';
    
    container.innerHTML = players.map(player => `
        <div class="player-card" onclick="showPlayerDetail(${JSON.stringify(player).replace(/"/g, '&quot;')})">
            <div class="player-name">${player.first_name} ${player.last_name}</div>
            <div class="player-info">
                <span>${getPositionName(player.position)}</span>
                ${player.team ? `<span>${player.team}</span>` : ''}
            </div>
            <div class="player-stats">
                <strong>Email:</strong> ${player.email}<br>
                <strong>Username:</strong> ${player.username}
                ${player.height ? `<br><strong>Altura:</strong> ${player.height}m` : ''}
                ${player.weight ? `<br><strong>Peso:</strong> ${player.weight}kg` : ''}
            </div>
            <div class="player-actions">
                <button class="btn btn-secondary btn-small" onclick="event.stopPropagation(); editPlayer(${player.id})">
                    <i class="fas fa-edit"></i> Editar
                </button>
            </div>
        </div>
    `).join('');
}

function getPositionName(position) {
    const positions = {
        'pitcher': 'Pitcher',
        'catcher': 'Catcher',
        'first_base': 'Primeira Base',
        'second_base': 'Segunda Base',
        'third_base': 'Terceira Base',
        'shortstop': 'Shortstop',
        'left_field': 'Campo Esquerdo',
        'center_field': 'Campo Central',
        'right_field': 'Campo Direito'
    };
    return positions[position] || position || 'N/A';
}

function loadPlayerDetail(player) {
    // Load overview
    const overview = document.getElementById('player-overview');
    overview.innerHTML = `
        <div class="player-detail-card">
            <div class="player-header">
                <div class="player-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="player-basic-info">
                    <h3>${player.first_name} ${player.last_name}</h3>
                    <p class="player-position">${getPositionName(player.position)}</p>
                    ${player.team ? `<p class="player-team"><i class="fas fa-users"></i> ${player.team}</p>` : ''}
                </div>
            </div>
            
            <div class="player-details-grid">
                <div class="detail-section">
                    <h4><i class="fas fa-id-card"></i> Informações Pessoais</h4>
                    <div class="detail-item">
                        <span class="label">Email:</span>
                        <span class="value">${player.email}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Username:</span>
                        <span class="value">${player.username}</span>
                    </div>
                </div>
                
                ${player.height || player.weight ? `
                <div class="detail-section">
                    <h4><i class="fas fa-ruler"></i> Características Físicas</h4>
                    ${player.height ? `
                    <div class="detail-item">
                        <span class="label">Altura:</span>
                        <span class="value">${player.height}m</span>
                    </div>` : ''}
                    ${player.weight ? `
                    <div class="detail-item">
                        <span class="label">Peso:</span>
                        <span class="value">${player.weight}kg</span>
                    </div>` : ''}
                </div>` : ''}
                
                ${player.strengths || player.weaknesses ? `
                <div class="detail-section">
                    <h4><i class="fas fa-chart-line"></i> Avaliação Técnica</h4>
                    ${player.strengths ? `
                    <div class="detail-item">
                        <span class="label">Pontos Fortes:</span>
                        <span class="value">${player.strengths}</span>
                    </div>` : ''}
                    ${player.weaknesses ? `
                    <div class="detail-item">
                        <span class="label">Áreas de Melhoria:</span>
                        <span class="value">${player.weaknesses}</span>
                    </div>` : ''}
                </div>` : ''}
            </div>
        </div>
    `;
}

async function loadTrainings() {
    try {
        const response = await makeRequest('/training/');
        const data = await response.json();
        
        if (response.ok) {
            displayTrainings(data.trainings || data);
        } else {
            showNotification('Erro ao carregar treinos', true);
        }
    } catch (error) {
        showNotification('Erro de conexão', true);
        console.error('Load trainings error:', error);
    }
}

function displayTrainings(trainings) {
    const container = document.getElementById('trainings-list');
    
    if (!trainings || trainings.length === 0) {
        container.innerHTML = '<p>Nenhum treino encontrado.</p>';
        return;
    }
    
    container.innerHTML = trainings.map(training => `
        <div class="training-card">
            <div class="training-title">${training.title}</div>
            <div class="training-meta">
                <span>${training.category}</span>
                <span>${training.difficulty}</span>
                <span>${training.duration} min</span>
            </div>
            <div class="training-description">
                ${training.description || 'Sem descrição'}
            </div>
            ${training.exercises && training.exercises.length > 0 ? `
                <div class="exercises-list">
                    <h4>Exercícios:</h4>
                    ${training.exercises.map(exercise => `
                        <div class="exercise-item">
                            <span>${exercise.name}</span>
                            <span>${exercise.sets}x${exercise.reps} - ${exercise.weight || 'Peso corporal'}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Player management functions
function editPlayer(playerId) {
    showNotification('Funcionalidade de edição em desenvolvimento', false);
}

function assignTraining() {
    showNotification('Funcionalidade de atribuição de treino em desenvolvimento', false);
}

async function addPlayer(event) {
    event.preventDefault();
    
    const playerData = {
        first_name: document.getElementById('player-first-name').value,
        last_name: document.getElementById('player-last-name').value,
        username: document.getElementById('player-username').value,
        email: document.getElementById('player-email').value,
        password: document.getElementById('player-password').value,
        position: document.getElementById('player-position').value,
        team: document.getElementById('player-team').value || null,
        height: parseFloat(document.getElementById('player-height').value) || null,
        weight: parseFloat(document.getElementById('player-weight').value) || null,
        strengths: document.getElementById('player-strengths').value || null,
        weaknesses: document.getElementById('player-weaknesses').value || null
    };
    
    try {
        const response = await makeRequest('/trainer/players', {
            method: 'POST',
            body: JSON.stringify(playerData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Jogador cadastrado com sucesso!');
            // Clear form
            event.target.reset();
            // Go back to players page
            showPlayersPage();
        } else {
            showNotification(data.message || 'Erro ao cadastrar jogador', true);
        }
    } catch (error) {
        showNotification('Erro de conexão', true);
        console.error('Add player error:', error);
    }
}

// AI functions
async function getPlayerTips(event) {
    event.preventDefault();
    
    if (!selectedPlayer) {
        showNotification('Nenhum jogador selecionado', true);
        return;
    }
    
    const category = document.getElementById('tips-category').value;
    const resultContainer = document.getElementById('player-tips-result');
    
    resultContainer.innerHTML = '<p>Gerando dicas personalizadas...</p>';
    
    try {
        const response = await makeRequest('/ai/workout-tips', {
            method: 'POST',
            body: JSON.stringify({ 
                category,
                player_info: {
                    position: selectedPlayer.position,
                    strengths: selectedPlayer.strengths,
                    weaknesses: selectedPlayer.weaknesses
                }
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            resultContainer.innerHTML = data.tips || 'Nenhuma dica disponível.';
        } else {
            resultContainer.innerHTML = `Erro: ${data.message || 'Não foi possível obter dicas'}`;
        }
    } catch (error) {
        resultContainer.innerHTML = 'Erro de conexão com o serviço de AI.';
        console.error('AI tips error:', error);
    }
} 