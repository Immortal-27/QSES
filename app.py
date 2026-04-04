"""
Quantum-Simulated Email Security (QSES) — Flask Application

A hackathon project demonstrating quantum key distribution concepts
through a classical simulation of the BB84 protocol with AES-256-GCM encryption.

DISCLAIMER: This is a SIMULATION of quantum key exchange using classical computing.
Real quantum key distribution requires dedicated quantum hardware and optical channels.
"""

from flask import Flask, render_template, request, jsonify
from quantum_sim import full_bb84_exchange, QUBIT_STATES
from crypto_utils import encrypt_message, decrypt_message
from cryptography.exceptions import InvalidTag
from dataclasses import asdict

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main application page."""
    return render_template("index.html")


@app.route("/api/simulate-qkd", methods=["POST"])
def simulate_qkd():
    """
    Run the BB84 quantum key exchange simulation.

    Request JSON:
        n_qubits (int): Number of qubits to simulate (default: 256)
        eavesdropper (bool): Whether to simulate an eavesdropper (default: false)

    Returns JSON with full protocol details and step-by-step results.
    """
    data = request.get_json(force=True)
    n_qubits = min(int(data.get("n_qubits", 256)), 1024)  # Cap at 1024
    with_eve = bool(data.get("eavesdropper", False))

    result = full_bb84_exchange(n_qubits=n_qubits, with_eavesdropper=with_eve)

    # Prepare visualization-friendly data (first 20 qubits for the table)
    display_count = min(20, n_qubits)
    qubit_table = []
    for i in range(display_count):
        alice_state = QUBIT_STATES.get((result.alice_bits[i], result.alice_bases[i]), "?")
        bases_match = result.alice_bases[i] == result.bob_bases[i]
        qubit_table.append({
            "index": i,
            "alice_bit": result.alice_bits[i],
            "alice_basis": result.alice_bases[i],
            "alice_state": alice_state,
            "bob_basis": result.bob_bases[i],
            "bob_bit": result.bob_measured_bits[i],
            "bases_match": bases_match,
            "kept": i in result.matching_indices,
        })

    response = {
        "success": True,
        "simulation": "BB84 Quantum Key Distribution (Classical Simulation)",
        "disclaimer": "This is a classical simulation. Real QKD requires quantum hardware.",
        "n_qubits": n_qubits,
        "eavesdropper_present": with_eve,
        "channel_secure": result.channel_secure,
        "error_rate": round(result.error_rate * 100, 2),
        "error_threshold": 11.0,
        "sifted_key_length": len(result.sifted_key_alice),
        "final_key_length": len(result.final_key_bits),
        "final_key_hex": result.final_key_hex,
        "qubit_table": qubit_table,
        "protocol_steps": result.protocol_steps,
        "stats": {
            "total_qubits": n_qubits,
            "matching_bases": len(result.matching_indices),
            "matching_rate": round(len(result.matching_indices) / n_qubits * 100, 1),
            "sample_size": len(result.sample_indices),
            "errors_detected": sum(1 for a, b in zip(result.sample_alice, result.sample_bob) if a != b),
        }
    }

    return jsonify(response)


@app.route("/api/encrypt", methods=["POST"])
def encrypt():
    """
    Encrypt an email message using the quantum-derived key.

    Request JSON:
        message (str): The email content to encrypt
        key (str): Hex key from BB84 simulation

    Returns JSON with encrypted ciphertext and metadata.
    """
    data = request.get_json(force=True)
    message = data.get("message", "")
    key_hex = data.get("key", "")

    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400
    if not key_hex:
        return jsonify({"success": False, "error": "Key is required. Run QKD simulation first."}), 400

    try:
        result = encrypt_message(message, key_hex)
        return jsonify({
            "success": True,
            "encrypted": result,
            "original_length": len(message),
            "ciphertext_length": len(result["ciphertext"]),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/decrypt", methods=["POST"])
def decrypt():
    """
    Decrypt an encrypted message using the quantum-derived key.

    Request JSON:
        nonce (str): Base64-encoded nonce
        ciphertext (str): Base64-encoded ciphertext
        key (str): Hex key from BB84 simulation

    Returns JSON with the decrypted plaintext.
    """
    data = request.get_json(force=True)
    nonce = data.get("nonce", "")
    ciphertext = data.get("ciphertext", "")
    key_hex = data.get("key", "")

    if not all([nonce, ciphertext, key_hex]):
        return jsonify({"success": False, "error": "Missing nonce, ciphertext, or key"}), 400

    try:
        plaintext = decrypt_message(nonce, ciphertext, key_hex)
        return jsonify({
            "success": True,
            "plaintext": plaintext,
        })
    except InvalidTag:
        return jsonify({
            "success": False,
            "error": "Decryption failed — ciphertext integrity check failed. "
                    "The message may have been tampered with or the wrong key was used.",
            "tampered": True,
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Quantum-Simulated Email Security (QSES)")
    print("  ⚛️  BB84 Protocol Simulation + AES-256-GCM Encryption")
    print("=" * 60)
    print("  DISCLAIMER: Classical simulation — not real QKD!")
    print("=" * 60)
    print(f"\n  🌐 Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
