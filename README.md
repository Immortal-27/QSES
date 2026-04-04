# ⚛️ QSES — Quantum-Simulated Email Security

> **A classical simulation of quantum key distribution (BB84 protocol) for email encryption,
> with real-time eavesdropping detection and AES-256-GCM authenticated encryption.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask)](https://flask.palletsprojects.com)
[![AES-256-GCM](https://img.shields.io/badge/Encryption-AES--256--GCM-green)](https://en.wikipedia.org/wiki/Galois/Counter_Mode)

---

## 🚨 Important Disclaimer

**This is a CLASSICAL SIMULATION of quantum key exchange.** Real quantum key distribution (QKD) requires:
- Dedicated quantum hardware (single-photon sources, detectors)
- Optical fiber or free-space quantum channels
- Distance limits (~100km without quantum repeaters)

This project uses Python's `secrets` module for cryptographically secure randomness to faithfully model the BB84 protocol's behavior without quantum hardware.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **BB84 Protocol Simulation** | Step-by-step visualization of quantum key exchange (qubit encoding, basis measurement, key sifting) |
| **AES-256-GCM Encryption** | NIST-approved authenticated encryption for email messages using quantum-derived keys |
| **Eavesdropping Detection** | Real-time error rate gauge showing how Eve's interception introduces detectable errors (~25% QBER) |
| **Interactive UI** | Premium dark theme with quantum particle animations, glassmorphism, and micro-interactions |

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py

# 3. Open in browser
# → http://127.0.0.1:5000
```

---

## 🏗️ Architecture

```
QSES/
├── app.py              # Flask routes (API endpoints)
├── quantum_sim.py      # BB84 protocol simulation engine
├── crypto_utils.py     # AES-256-GCM encryption/decryption
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Main SPA template
└── static/
    ├── css/style.css   # Premium quantum-themed dark UI
    └── js/main.js      # Canvas particles, API calls, animations
```

---

## 🔬 How BB84 Works (Simplified)

1. **Alice** generates random bits and encodes each in a random basis (+ or ×)
2. **Alice** sends qubits to **Bob** through a quantum channel
3. **Bob** measures each qubit using a randomly chosen basis
4. **Alice & Bob** publicly compare bases (not values) — keep only matching-basis bits
5. They sacrifice some bits to **estimate the error rate**
6. If error rate < 11% → channel is **secure**; otherwise → **eavesdropper detected!**

### Why Eavesdropping is Detectable

When Eve intercepts a qubit, she must measure it (collapsing its quantum state) and re-send it. Since she doesn't know Alice's basis, ~50% of the time she measures in the wrong basis, introducing a ~25% error rate that Alice and Bob can detect.

---

## 🔐 Security Details

| Component | Standard | Notes |
|-----------|----------|-------|
| Encryption | AES-256-GCM | Authenticated encryption (confidentiality + integrity) |
| Key Derivation | HKDF-SHA256 | Stretches BB84 key material into uniform AES key |
| Randomness | `secrets` module | CSPRNG — suitable for cryptographic use |
| Protocol | BB84 (simulated) | Classical simulation, not real quantum |

---

## 🏆 Why This Wins at Hackathons

1. **Technically accurate** — No false claims about quantum hardware
2. **Solves real problems** — Email key exchange vulnerabilities
3. **Educational impact** — Teaches quantum concepts through interactive simulation
4. **Stunning UI** — Premium dark theme with actual particle physics animations
5. **Zero setup friction** — `pip install` + `python app.py` = done

---

## 📄 License

MIT — Built for hackathons, education, and open-source learning.
