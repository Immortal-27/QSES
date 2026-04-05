"""
Quantum-Simulated Email Security (QSES) — Flask Application

A hackathon project demonstrating quantum key distribution concepts
through a classical simulation of the BB84 protocol with AES-256-GCM encryption.

DISCLAIMER: This is a SIMULATION of quantum key exchange using classical computing.
Real quantum key distribution requires dedicated quantum hardware and optical channels.
"""

import os
import uuid
from dotenv import load_dotenv

# Load environment variables from .env BEFORE anything else
load_dotenv()

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from quantum_sim import full_bb84_exchange, QUBIT_STATES
from crypto_utils import encrypt_message, decrypt_message
from smtp_service import SMTPService
from cryptography.exceptions import InvalidTag

app = Flask(__name__)
import secrets
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(24))

# Initialize SMTP service (reads credentials from env vars loaded above)
smtp = SMTPService()


@app.route("/chain.glb")
def serve_chain_model():
    """Serve the 3D chain model from the chainbg static folder."""
    return send_from_directory(os.path.join(app.static_folder, "chainbg"), "chain.glb")


@app.route("/")
def index():
    """Serve the main application page."""
    return render_template("index.html")


@app.route("/login")
def login():
    """Serve the authentication page."""
    return render_template("login.html")


@app.route("/app")
def app_page():
    """Post-login redirect — serves the main app page."""
    return render_template("index.html")


@app.route("/profile")
def profile():
    """Serve the profile dashboard."""
    if "profile" not in session:
        session["profile"] = {
            "name": "Quantum Agent",
            "handle": "@agent_q",
            "bio": "Initialize quantum link to begin.",
            "avatar": "cyber"
        }
    if "stats" not in session:
        session["stats"] = {
            "keys_generated": 0,
            "total_qubits_sent": 0,
            "messages_encrypted": 0,
            "messages_decrypted": 0
        }
    if "activity_log" not in session:
        session["activity_log"] = []

    return render_template(
        "profile.html",
        profile=session["profile"],
        stats=session["stats"],
        activity_log=session["activity_log"]
    )


@app.route("/api/profile/update", methods=["POST"])
def update_profile():
    """Update user profile in session."""
    data = request.get_json(force=True)
    session["profile"] = {
        "name": data.get("name", "Quantum Agent"),
        "handle": data.get("handle", "@agent_q"),
        "bio": data.get("bio", ""),
        "avatar": data.get("avatar", "cyber")
    }
    session.modified = True
    return jsonify({"success": True})


@app.route("/decrypt")
def decrypt_page():
    """
    Decrypt landing page — linked from emails.

    Accepts query params ?nonce=...&ciphertext=...&mid=... and serves the
    main page. JavaScript reads the URL params, pre-fills the decrypt
    form, and auto-retrieves the encryption key from the session if the
    user is the same one who sent the email.
    """
    return render_template("index.html")


@app.route("/api/firebase-config")
def firebase_config():
    """Serve Firebase client configuration from environment variables."""
    return jsonify({
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", ""),
        "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", ""),
    })


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
        nonce (str): Hex-encoded nonce
        ciphertext (str): Hex-encoded ciphertext
        hmac (str): Hex-encoded HMAC-SHA256 tag
        key (str): Hex key from BB84 simulation

    Returns JSON with the decrypted plaintext.
    """
    data = request.get_json(force=True)
    nonce = data.get("nonce", "")
    ciphertext = data.get("ciphertext", "")
    hmac_tag = data.get("hmac", "")
    key_hex = data.get("key", "")

    if not all([nonce, ciphertext, key_hex]):
        return jsonify({"success": False, "error": "Missing nonce, ciphertext, or key"}), 400

    try:
        plaintext = decrypt_message(nonce, ciphertext, key_hex, hmac_tag=hmac_tag)
        return jsonify({
            "success": True,
            "plaintext": plaintext,
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "tampered": True,
        }), 400
    except InvalidTag:
        return jsonify({
            "success": False,
            "error": "Decryption failed — ciphertext integrity check failed. "
                    "The message may have been tampered with or the wrong key was used.",
            "tampered": True,
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# SMTP Routes
# ============================================================

@app.route("/api/smtp/status", methods=["GET"])
def smtp_status():
    """
    Check whether SMTP is configured and ready.

    Returns JSON with configuration status (password is never exposed).
    """
    status = smtp.get_status()
    return jsonify({"success": True, **status})


@app.route("/api/smtp/configure", methods=["POST"])
def smtp_configure():
    """
    Configure SMTP credentials at runtime (in-memory override).

    Request JSON:
        server (str): SMTP server hostname
        port (int): SMTP server port
        email (str): Sender email address
        password (str): Sender app password

    Also runs a connection test to validate the credentials.
    """
    data = request.get_json(force=True)
    server = data.get("server", "smtp.gmail.com")
    port = int(data.get("port", 587))
    email = data.get("email", "")
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    # Apply credentials in memory first (don't save to .env yet)
    smtp.server = server
    smtp.port = port
    smtp.email = email
    smtp.password = password

    # Test the connection
    test_result = smtp.test_connection()

    if test_result["success"]:
        # Connection works — now persist to .env
        smtp.save_to_env()

    return jsonify({
        "success": test_result["success"],
        "message": test_result["message"],
        "status": smtp.get_status(),
    })


@app.route("/api/smtp/send", methods=["POST"])
def smtp_send():
    """
    Encrypt a message and send it via SMTP in one step.

    Request JSON:
        recipient (str): Destination email address
        subject (str): Email subject line
        message (str): Plaintext message to encrypt and send
        key (str): Hex key from BB84 simulation

    The message is encrypted with AES-256-GCM using the provided key,
    then the encrypted payload is sent as a formatted email via SMTP.
    """
    data = request.get_json(force=True)
    recipient = data.get("recipient", "")
    subject = data.get("subject", "Encrypted Message")
    message = data.get("message", "")
    key_hex = data.get("key", "")

    # Validate inputs
    if not recipient or "@" not in recipient:
        return jsonify({"success": False, "error": "Valid recipient email is required."}), 400
    if not message:
        return jsonify({"success": False, "error": "Message body is required."}), 400
    if not key_hex:
        return jsonify({"success": False, "error": "Encryption key is required. Run BB84 simulation first."}), 400
    if not smtp.is_configured():
        return jsonify({"success": False, "error": "SMTP is not configured. Set your credentials first."}), 400

    try:
        # Step 1: Encrypt the message
        encrypted_payload = encrypt_message(message, key_hex)

        # Step 2: Generate a unique message ID and store the key in the session
        message_id = uuid.uuid4().hex[:12]
        if "decrypt_keys" not in session:
            session["decrypt_keys"] = {}
        session["decrypt_keys"][message_id] = key_hex
        session.modified = True

        # Step 3: Determine base URL for the decrypt link in the email
        base_url = request.url_root.rstrip("/")

        # Step 4: Send via SMTP (pass message_id so it's included in the decrypt URL)
        send_result = smtp.send_encrypted_email(
            recipient=recipient,
            subject=subject,
            encrypted_payload=encrypted_payload,
            original_length=len(message),
            base_url=base_url,
            message_id=message_id,
        )

        if send_result["success"]:
            return jsonify({
                "success": True,
                "message": send_result["message"],
                "details": send_result.get("details", {}),
                "encrypted": encrypted_payload,
            })
        else:
            return jsonify({
                "success": False,
                "error": send_result["message"],
            }), 500

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to encrypt and send: {str(e)}"}), 500


@app.route("/api/decrypt-key/<message_id>", methods=["GET"])
def get_decrypt_key(message_id):
    """
    Retrieve the stored encryption key for a specific message.

    The key is only available if the current session is the same one
    that sent the original email (same browser/user who encrypted).
    This allows the decrypt page to auto-fill the key field.
    """
    decrypt_keys = session.get("decrypt_keys", {})
    key = decrypt_keys.get(message_id)

    if key:
        return jsonify({"success": True, "key": key})
    else:
        return jsonify({
            "success": False,
            "error": "No key found for this message. You may need to enter the key manually."
        }), 404


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Quantum-Simulated Email Security (QSES)")
    print("  [*] BB84 Protocol Simulation + AES-256-GCM Encryption")
    print("=" * 60)
    print("  DISCLAIMER: Classical simulation -- not real QKD!")
    print("=" * 60)

    # Show SMTP status
    if smtp.is_configured():
        status = smtp.get_status()
        print(f"\n  [SMTP] Configured ({status['masked_email']} via {status['server']})")
    else:
        print("\n  [SMTP] Not configured -- edit .env to add credentials")

    print(f"\n  [*] Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
