/**
 * QSES — Quantum-Simulated Email Security
 * Frontend Logic: Canvas particles, BB84 visualization, API calls, animations
 */

// ============================================================
// Quantum Particle Canvas Background
// ============================================================
class QuantumParticles {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.particles = [];
        this.connections = [];
        this.mouse = { x: null, y: null };
        this.resize();
        this.init();
        this.animate();

        window.addEventListener('resize', () => this.resize());
        window.addEventListener('mousemove', (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    init() {
        const count = Math.min(80, Math.floor(window.innerWidth * window.innerHeight / 18000));
        this.particles = [];
        for (let i = 0; i < count; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                vx: (Math.random() - 0.5) * 0.4,
                vy: (Math.random() - 0.5) * 0.4,
                radius: Math.random() * 2 + 0.5,
                color: this.randomColor(),
                alpha: Math.random() * 0.5 + 0.1,
                pulse: Math.random() * Math.PI * 2,
            });
        }
    }

    randomColor() {
        const colors = [
            '0, 229, 255',   // cyan
            '179, 136, 255', // purple
            '255, 64, 129',  // pink
            '105, 240, 174', // green
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Update & draw particles
        for (const p of this.particles) {
            p.x += p.vx;
            p.y += p.vy;
            p.pulse += 0.02;

            // Boundary wrap
            if (p.x < -10) p.x = this.canvas.width + 10;
            if (p.x > this.canvas.width + 10) p.x = -10;
            if (p.y < -10) p.y = this.canvas.height + 10;
            if (p.y > this.canvas.height + 10) p.y = -10;

            // Mouse interaction
            if (this.mouse.x !== null) {
                const dx = this.mouse.x - p.x;
                const dy = this.mouse.y - p.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 150) {
                    p.vx -= dx * 0.00005;
                    p.vy -= dy * 0.00005;
                }
            }

            const pulseAlpha = p.alpha + Math.sin(p.pulse) * 0.1;
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${p.color}, ${pulseAlpha})`;
            this.ctx.fill();

            // Glow
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.radius * 3, 0, Math.PI * 2);
            this.ctx.fillStyle = `rgba(${p.color}, ${pulseAlpha * 0.15})`;
            this.ctx.fill();
        }

        // Draw connections
        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const a = this.particles[i];
                const b = this.particles[j];
                const dx = a.x - b.x;
                const dy = a.y - b.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    const opacity = (1 - dist / 120) * 0.12;
                    this.ctx.beginPath();
                    this.ctx.moveTo(a.x, a.y);
                    this.ctx.lineTo(b.x, b.y);
                    this.ctx.strokeStyle = `rgba(0, 229, 255, ${opacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        }

        requestAnimationFrame(() => this.animate());
    }
}

// ============================================================
// App State
// ============================================================
const state = {
    currentKey: null,
    lastSimulation: null,
    secureErrorRate: null,
    eveErrorRate: null,
};

// ============================================================
// DOM Ready
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Init quantum canvas
    const canvas = document.getElementById('quantum-canvas');
    if (canvas) new QuantumParticles(canvas);

    // Qubit slider
    const slider = document.getElementById('n-qubits');
    const sliderValue = document.getElementById('n-qubits-value');
    if (slider && sliderValue) {
        slider.addEventListener('input', () => {
            sliderValue.textContent = slider.value;
        });
    }

    // Nav active state on scroll
    const sections = document.querySelectorAll('.section, .hero');
    const navLinks = document.querySelectorAll('.nav-link');
    window.addEventListener('scroll', () => {
        let current = '';
        sections.forEach(section => {
            const top = section.offsetTop - 100;
            if (window.scrollY >= top) current = section.id;
        });
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.dataset.section === current) link.classList.add('active');
        });
    });

    // Eve toggle
    const eveToggle = document.getElementById('eve-toggle');
    if (eveToggle) {
        eveToggle.addEventListener('change', () => {
            const interceptor = document.getElementById('eve-interceptor');
            const channel = document.getElementById('eve-channel');
            const safeLbl = document.querySelector('.eve-label-safe');
            const dangerLbl = document.querySelector('.eve-label-danger');

            if (eveToggle.checked) {
                interceptor.classList.add('active');
                channel.classList.add('intercepted');
                dangerLbl.classList.add('active');
                safeLbl.classList.add('dimmed');
            } else {
                interceptor.classList.remove('active');
                channel.classList.remove('intercepted');
                dangerLbl.classList.remove('active');
                safeLbl.classList.remove('dimmed');
            }
        });
    }

    // Button handlers
    document.getElementById('btn-simulate')?.addEventListener('click', runSimulation);
    document.getElementById('btn-encrypt')?.addEventListener('click', encryptMessage);
    document.getElementById('btn-decrypt')?.addEventListener('click', decryptMessage);
    document.getElementById('btn-eve-simulate')?.addEventListener('click', runEveDetection);
    document.getElementById('btn-copy-key')?.addEventListener('click', copyKey);
});

// ============================================================
// BB84 Simulation
// ============================================================
async function runSimulation() {
    const btn = document.getElementById('btn-simulate');
    const nQubits = parseInt(document.getElementById('n-qubits').value);

    btn.classList.add('loading');
    btn.disabled = true;

    try {
        const res = await fetch('/api/simulate-qkd', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ n_qubits: nQubits, eavesdropper: false }),
        });
        const data = await res.json();

        if (data.success) {
            state.currentKey = data.final_key_hex;
            state.lastSimulation = data;
            renderProtocolSteps(data.protocol_steps);
            renderQubitTable(data.qubit_table);
            renderStats(data);
            renderKeyDisplay(data);
            updateEncryptionKey();
        }
    } catch (err) {
        console.error('Simulation error:', err);
        showError('protocol-steps', 'Failed to run simulation. Is the server running?');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

function renderProtocolSteps(steps) {
    const container = document.getElementById('protocol-steps');
    container.innerHTML = '';

    steps.forEach((step, i) => {
        const card = document.createElement('div');
        const type = step.title.includes('⚠️') || step.title.includes('🚨')
            ? 'danger'
            : step.title.includes('✅') || step.title.includes('SECURE')
            ? 'secure'
            : 'neutral';

        card.className = `step-card ${type}`;
        card.style.animationDelay = `${i * 0.15}s`;
        card.innerHTML = `
            <div class="step-header">
                <div class="step-number">${step.step}</div>
                <div class="step-title">${step.title}</div>
            </div>
            <div class="step-desc">${step.description}</div>
            <div class="step-detail">${step.detail}</div>
        `;
        container.appendChild(card);
    });
}

function renderQubitTable(qubits) {
    const wrapper = document.getElementById('qubit-table-wrapper');
    const tbody = document.getElementById('qubit-table-body');

    wrapper.style.display = 'block';
    tbody.innerHTML = '';

    qubits.forEach(q => {
        const tr = document.createElement('tr');
        const matchClass = q.bases_match ? 'match-yes' : 'match-no';
        tr.innerHTML = `
            <td>${q.index}</td>
            <td>${q.alice_bit}</td>
            <td class="basis-cell">${q.alice_basis}</td>
            <td class="state-cell">${q.alice_state}</td>
            <td class="basis-cell">${q.bob_basis}</td>
            <td>${q.bob_bit}</td>
            <td class="${matchClass}">${q.bases_match ? '✓ Keep' : '✗ Discard'}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderStats(data) {
    const grid = document.getElementById('stats-grid');
    grid.style.display = 'grid';

    document.getElementById('stat-total').textContent = data.stats.total_qubits;
    document.getElementById('stat-matching').textContent = `${data.stats.matching_bases} (${data.stats.matching_rate}%)`;
    document.getElementById('stat-key-len').textContent = data.final_key_length;

    const errorEl = document.getElementById('stat-error');
    const errorIcon = document.getElementById('stat-error-icon');
    errorEl.textContent = `${data.error_rate}%`;

    if (data.channel_secure) {
        errorEl.style.color = 'var(--green)';
        errorIcon.textContent = '✅';
    } else {
        errorEl.style.color = 'var(--red)';
        errorIcon.textContent = '🚨';
    }
}

function renderKeyDisplay(data) {
    const display = document.getElementById('key-display');
    display.style.display = 'block';

    const statusEl = document.getElementById('key-status');
    const valueEl = document.getElementById('key-value');
    const metaEl = document.getElementById('key-meta');

    valueEl.textContent = data.final_key_hex;

    if (data.channel_secure) {
        statusEl.textContent = 'SECURE';
        statusEl.className = 'key-status secure';
    } else {
        statusEl.textContent = 'COMPROMISED';
        statusEl.className = 'key-status compromised';
    }

    metaEl.textContent = `${data.final_key_length} bits | AES-256-GCM ready | QBER: ${data.error_rate}%`;
}

function updateEncryptionKey() {
    if (state.currentKey) {
        const keyInput = document.getElementById('encrypt-key');
        const badge = document.getElementById('key-source-badge');
        const decryptKey = document.getElementById('decrypt-key');

        keyInput.value = state.currentKey;
        badge.textContent = 'BB84 Key';
        badge.className = 'key-source-badge has-key';

        if (decryptKey) decryptKey.value = state.currentKey;
    }
}

async function copyKey() {
    if (state.currentKey) {
        try {
            await navigator.clipboard.writeText(state.currentKey);
            const btn = document.getElementById('btn-copy-key');
            btn.textContent = '✅ Copied!';
            setTimeout(() => { btn.textContent = '📋 Copy'; }, 2000);
        } catch {
            // Fallback
            const ta = document.createElement('textarea');
            ta.value = state.currentKey;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
    }
}

// ============================================================
// Encryption / Decryption
// ============================================================
async function encryptMessage() {
    const message = document.getElementById('encrypt-message').value;
    const key = document.getElementById('encrypt-key').value;
    const resultDiv = document.getElementById('encrypt-result');

    if (!message) {
        resultDiv.innerHTML = `<div class="result-placeholder"><div class="placeholder-icon">⚠️</div><p>Please enter a message to encrypt</p></div>`;
        return;
    }
    if (!key) {
        resultDiv.innerHTML = `<div class="result-placeholder"><div class="placeholder-icon">🔑</div><p>Run the BB84 simulation first to generate a key</p></div>`;
        return;
    }

    try {
        const res = await fetch('/api/encrypt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, key }),
        });
        const data = await res.json();

        if (data.success) {
            const enc = data.encrypted;
            resultDiv.innerHTML = `
                <div class="result-data">
                    <div class="result-field">
                        <div class="result-field-label">Algorithm</div>
                        <div class="result-field-value">${enc.algorithm} • ${enc.key_derivation} • ${enc.key_source}</div>
                    </div>
                    <div class="result-field">
                        <div class="result-field-label">Nonce (Base64)</div>
                        <div class="result-field-value">${enc.nonce}</div>
                    </div>
                    <div class="result-field">
                        <div class="result-field-label">Ciphertext (Base64)</div>
                        <div class="result-field-value">${enc.ciphertext}</div>
                    </div>
                    <div class="result-field">
                        <div class="result-field-label">Original → Encrypted</div>
                        <div class="result-field-value">${data.original_length} chars → ${data.ciphertext_length} chars</div>
                    </div>
                </div>
            `;

            // Auto-fill decrypt fields
            document.getElementById('decrypt-ciphertext').value = enc.ciphertext;
            document.getElementById('decrypt-nonce').value = enc.nonce;
            document.getElementById('decrypt-key').value = key;
        } else {
            resultDiv.innerHTML = `<div class="result-data"><div class="result-field"><div class="result-field-label">Error</div><div class="result-field-value error">${data.error}</div></div></div>`;
        }
    } catch (err) {
        resultDiv.innerHTML = `<div class="result-data"><div class="result-field"><div class="result-field-value error">Network error — is the server running?</div></div></div>`;
    }
}

async function decryptMessage() {
    const ciphertext = document.getElementById('decrypt-ciphertext').value;
    const nonce = document.getElementById('decrypt-nonce').value;
    const key = document.getElementById('decrypt-key').value;
    const resultDiv = document.getElementById('decrypt-result');

    if (!ciphertext || !nonce || !key) {
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `<div class="result-field"><div class="result-field-value error">Please fill in all fields (ciphertext, nonce, and key)</div></div>`;
        return;
    }

    try {
        const res = await fetch('/api/decrypt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ciphertext, nonce, key }),
        });
        const data = await res.json();

        resultDiv.style.display = 'block';
        if (data.success) {
            resultDiv.innerHTML = `
                <div class="result-field" style="margin-top: 16px;">
                    <div class="result-field-label">Decrypted Message</div>
                    <div class="result-field-value success">${escapeHtml(data.plaintext)}</div>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="result-field" style="margin-top: 16px;">
                    <div class="result-field-label">Decryption Failed</div>
                    <div class="result-field-value error">${data.error}</div>
                </div>
            `;
        }
    } catch (err) {
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `<div class="result-field"><div class="result-field-value error">Network error</div></div>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// Eavesdropping Detection
// ============================================================
async function runEveDetection() {
    const btn = document.getElementById('btn-eve-simulate');
    const eveToggle = document.getElementById('eve-toggle');
    const withEve = eveToggle.checked;

    btn.classList.add('loading');
    btn.disabled = true;

    try {
        // Run both simulations for comparison
        const [secureRes, eveRes] = await Promise.all([
            fetch('/api/simulate-qkd', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ n_qubits: 256, eavesdropper: false }),
            }).then(r => r.json()),
            fetch('/api/simulate-qkd', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ n_qubits: 256, eavesdropper: true }),
            }).then(r => r.json()),
        ]);

        state.secureErrorRate = secureRes.error_rate;
        state.eveErrorRate = eveRes.error_rate;

        // Show the active scenario's gauge
        const activeRate = withEve ? eveRes.error_rate : secureRes.error_rate;
        const isSecure = activeRate < 11;

        renderGauge(activeRate, isSecure);
        renderComparison(secureRes.error_rate, eveRes.error_rate);

    } catch (err) {
        console.error('Eve detection error:', err);
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

function renderGauge(errorRate, isSecure) {
    const section = document.getElementById('gauge-section');
    const fill = document.getElementById('gauge-fill');
    const value = document.getElementById('gauge-value');
    const verdict = document.getElementById('gauge-verdict');

    section.style.display = 'block';

    // Arc calculation: total arc length ≈ 251
    const maxRate = 50;
    const ratio = Math.min(errorRate / maxRate, 1);
    const offset = 251 - (251 * ratio);

    fill.style.strokeDashoffset = offset;
    fill.className = 'gauge-fill' + (errorRate > 11 ? ' danger' : errorRate > 5 ? ' warning' : '');

    // Animate counter
    animateCounter(value, errorRate, '%');

    if (isSecure) {
        verdict.textContent = '✅ Channel is SECURE — No eavesdropper detected';
        verdict.className = 'gauge-verdict secure';
    } else {
        verdict.textContent = '🚨 EAVESDROPPER DETECTED — Key exchange compromised!';
        verdict.className = 'gauge-verdict compromised';
    }
}

function renderComparison(secureRate, eveRate) {
    const grid = document.getElementById('comparison-grid');
    grid.style.display = 'grid';

    document.getElementById('comp-secure-rate').textContent = `${secureRate.toFixed(1)}%`;
    document.getElementById('comp-danger-rate').textContent = `${eveRate.toFixed(1)}%`;

    // Animate bars
    setTimeout(() => {
        document.getElementById('comp-bar-secure').style.width = `${Math.max(secureRate * 2, 2)}%`;
        document.getElementById('comp-bar-danger').style.width = `${Math.min(eveRate * 2, 100)}%`;
    }, 300);
}

function animateCounter(element, targetValue, suffix = '') {
    const duration = 1200;
    const start = performance.now();
    const startVal = 0;

    function update(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        const current = startVal + (targetValue - startVal) * eased;
        element.textContent = `${current.toFixed(1)}${suffix}`;

        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

// ============================================================
// Utility: Error Display
// ============================================================
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    container.innerHTML = `
        <div class="step-placeholder">
            <div class="placeholder-icon">❌</div>
            <p style="color: var(--red);">${message}</p>
        </div>
    `;
}
