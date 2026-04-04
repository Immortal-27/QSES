"""
SMTP Service for Quantum-Simulated Email Security.

Handles sending encrypted email payloads via SMTP (TLS).
Credentials are loaded from environment variables (.env file).
"""

import smtplib
import ssl
import os
import re
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone


class SMTPService:
    """
    Manages SMTP connections and sends quantum-encrypted email payloads.

    Credentials are read from environment variables:
        SMTP_SERVER  — SMTP host (default: smtp.gmail.com)
        SMTP_PORT    — SMTP port (default: 587)
        SMTP_EMAIL   — Sender email address
        SMTP_PASSWORD — Sender app password
    """

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """Load SMTP configuration from environment variables."""
        self.server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.email = os.getenv("SMTP_EMAIL", "")
        self.password = os.getenv("SMTP_PASSWORD", "")

    def is_configured(self) -> bool:
        """Check if SMTP credentials are present (non-placeholder)."""
        if not self.email or not self.password:
            return False
        if self.email == "your-email@gmail.com":
            return False
        if self.password == "your-app-password-here":
            return False
        return True

    def get_status(self) -> dict:
        """Return current SMTP configuration status (never exposes password)."""
        configured = self.is_configured()
        return {
            "configured": configured,
            "server": self.server,
            "port": self.port,
            "email": self.email if configured else "",
            "masked_email": self._mask_email(self.email) if configured else "",
        }

    def configure(self, server: str, port: int, email: str, password: str):
        """
        Update SMTP credentials in memory and persist them to the .env file.
        """
        self.server = server
        self.port = port
        self.email = email
        self.password = password
        self.save_to_env()

    def save_to_env(self):
        """
        Write the current SMTP configuration back to the .env file.

        - If a key already exists in .env, its value is updated in place.
        - If a key is missing, it is appended.
        - Comments and other variables are preserved.
        """
        env_path = Path(__file__).parent / ".env"

        updates = {
            "SMTP_SERVER": self.server,
            "SMTP_PORT": str(self.port),
            "SMTP_EMAIL": self.email,
            "SMTP_PASSWORD": self.password,
        }

        # Read existing content (or start fresh)
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
        else:
            lines = [
                "# QSES — SMTP Configuration",
                "# Generated automatically",
                "",
            ]

        keys_written = set()

        # Update existing lines in place
        new_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip blank / comment lines — keep them as-is
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue

            # Match KEY=VALUE (with optional spaces around '=')
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
            if match:
                key = match.group(1)
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}")
                    keys_written.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Append any keys that weren't already in the file
        for key, value in updates.items():
            if key not in keys_written:
                new_lines.append(f"{key}={value}")

        # Write back with a trailing newline
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    def test_connection(self) -> dict:
        """
        Test the SMTP connection without sending an email.

        Returns:
            dict with 'success' (bool) and 'message' (str)
        """
        if not self.is_configured():
            return {
                "success": False,
                "message": "SMTP is not configured. Please set your credentials in the .env file or via the UI.",
            }

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.server, self.port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(self.email, self.password)
            return {
                "success": True,
                "message": f"Successfully connected to {self.server}:{self.port} as {self._mask_email(self.email)}",
            }
        except smtplib.SMTPAuthenticationError:
            is_gmail = "gmail" in self.server.lower()
            if is_gmail:
                hint = "For Gmail/Google Workspace, use an App Password (not your regular password)."
            else:
                hint = f"Verify your credentials are correct for {self.server}."
            return {
                "success": False,
                "message": f"Authentication failed. {hint}",
            }
        except smtplib.SMTPConnectError:
            return {
                "success": False,
                "message": f"Could not connect to {self.server}:{self.port}. Check server and port.",
            }
        except (TimeoutError, OSError) as e:
            return {
                "success": False,
                "message": f"Connection to {self.server}:{self.port} failed: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"SMTP error: {str(e)}",
            }

    def send_encrypted_email(
        self,
        recipient: str,
        subject: str,
        encrypted_payload: dict,
        original_length: int,
    ) -> dict:
        """
        Send an encrypted email payload via SMTP.

        Args:
            recipient: Destination email address
            subject: Email subject line
            encrypted_payload: dict with 'ciphertext', 'nonce', 'algorithm', etc.
            original_length: Length of the original plaintext message

        Returns:
            dict with 'success' (bool), 'message' (str), and optional metadata
        """
        if not self.is_configured():
            return {
                "success": False,
                "message": "SMTP is not configured. Set your credentials first.",
            }

        if not recipient or "@" not in recipient:
            return {
                "success": False,
                "message": "Invalid recipient email address.",
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.email
            msg["To"] = recipient
            msg["Subject"] = f"🔐 {subject} [QSES Encrypted]"
            msg["X-QSES-Algorithm"] = encrypted_payload.get("algorithm", "AES-256-GCM")
            msg["X-QSES-KeySource"] = encrypted_payload.get("key_source", "BB84-Simulated-QKD")

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            # Plain text version (for clients that don't render HTML)
            plain_body = self._build_plain_body(encrypted_payload, timestamp, original_length)
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))

            # HTML version
            html_body = self._build_html_body(encrypted_payload, timestamp, original_length, subject)
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # Send
            context = ssl.create_default_context()
            with smtplib.SMTP(self.server, self.port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(self.email, self.password)
                smtp.sendmail(self.email, recipient, msg.as_string())

            return {
                "success": True,
                "message": f"Encrypted email sent to {recipient}",
                "details": {
                    "from": self._mask_email(self.email),
                    "to": recipient,
                    "subject": msg["Subject"],
                    "timestamp": timestamp,
                    "algorithm": encrypted_payload.get("algorithm", "AES-256-GCM"),
                },
            }

        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "SMTP authentication failed. Check your credentials.",
            }
        except smtplib.SMTPRecipientsRefused:
            return {
                "success": False,
                "message": f"Recipient address '{recipient}' was refused by the server.",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask an email address for display (e.g., s***a@gmail.com)."""
        if not email or "@" not in email:
            return ""
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked = local[0] + "***"
        else:
            masked = local[0] + "***" + local[-1]
        return f"{masked}@{domain}"

    @staticmethod
    def _build_plain_body(payload: dict, timestamp: str, original_length: int) -> str:
        """Build a plain-text email body with the encrypted payload."""
        return (
            "═══════════════════════════════════════════════════\n"
            "  QUANTUM-SIMULATED ENCRYPTED MESSAGE (QSES)\n"
            "═══════════════════════════════════════════════════\n\n"
            "This email contains an encrypted message secured with\n"
            "a quantum-simulated key (BB84 protocol + AES-256-GCM + HMAC-SHA256).\n\n"
            "--- ENCRYPTED PAYLOAD ---\n\n"
            f"Algorithm:      {payload.get('algorithm', 'AES-256-GCM')}\n"
            f"Integrity:      {payload.get('integrity', 'HMAC-SHA256')}\n"
            f"Key Derivation: {payload.get('key_derivation', 'HKDF-SHA256')}\n"
            f"Key Source:     {payload.get('key_source', 'BB84-Simulated-QKD')}\n"
            f"Original Size:  {original_length} characters\n"
            f"Timestamp:      {timestamp}\n\n"
            f"Nonce (Hex):\n{payload.get('nonce', 'N/A')}\n\n"
            f"Ciphertext (Hex):\n{payload.get('ciphertext', 'N/A')}\n\n"
            f"HMAC-SHA256 Tag:\n{payload.get('hmac', 'N/A')}\n\n"
            "--- END ENCRYPTED PAYLOAD ---\n\n"
            "To decrypt this message, the recipient needs:\n"
            "1. The shared quantum-derived key (AES-256 hex)\n"
            "2. The nonce, ciphertext, and HMAC tag above\n"
            "3. The QSES decryption tool\n\n"
            "DISCLAIMER: This is a classical simulation of quantum\n"
            "key distribution — not real QKD hardware.\n"
        )

    @staticmethod
    def _build_html_body(payload: dict, timestamp: str, original_length: int, subject: str) -> str:
        """Build a styled HTML email body with the encrypted payload."""
        return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#07070e;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;padding:32px 24px;">

  <!-- Header -->
  <div style="text-align:center;padding:28px 20px;background:linear-gradient(135deg,#0d0d1a,#121230);border-radius:16px 16px 0 0;border:1px solid rgba(0,229,255,0.15);border-bottom:none;">
    <div style="font-size:32px;margin-bottom:8px;">⚛️🔐</div>
    <h1 style="margin:0;font-size:22px;font-weight:800;color:#e8eaf6;">Quantum-Encrypted Message</h1>
    <p style="margin:6px 0 0;font-size:12px;color:#5c6bc0;letter-spacing:1px;">QSES — QUANTUM-SIMULATED EMAIL SECURITY</p>
  </div>

  <!-- Subject -->
  <div style="padding:20px 24px;background:rgba(15,15,35,0.9);border-left:1px solid rgba(0,229,255,0.15);border-right:1px solid rgba(0,229,255,0.15);">
    <p style="margin:0;font-size:11px;color:#5c6bc0;text-transform:uppercase;letter-spacing:1px;">Subject</p>
    <p style="margin:4px 0 0;font-size:16px;color:#e8eaf6;font-weight:600;">{subject}</p>
  </div>

  <!-- Metadata -->
  <div style="padding:20px 24px;background:rgba(15,15,35,0.85);border-left:1px solid rgba(0,229,255,0.15);border-right:1px solid rgba(0,229,255,0.15);">
    <table style="width:100%;font-size:13px;color:#9fa8da;border-collapse:collapse;">
      <tr><td style="padding:6px 0;color:#5c6bc0;">Algorithm</td><td style="padding:6px 0;text-align:right;color:#00e5ff;">{payload.get('algorithm', 'AES-256-GCM')}</td></tr>
      <tr><td style="padding:6px 0;color:#5c6bc0;">Integrity</td><td style="padding:6px 0;text-align:right;color:#ff9100;">{payload.get('integrity', 'HMAC-SHA256')}</td></tr>
      <tr><td style="padding:6px 0;color:#5c6bc0;">Key Derivation</td><td style="padding:6px 0;text-align:right;color:#b388ff;">{payload.get('key_derivation', 'HKDF-SHA256')}</td></tr>
      <tr><td style="padding:6px 0;color:#5c6bc0;">Key Source</td><td style="padding:6px 0;text-align:right;color:#69f0ae;">{payload.get('key_source', 'BB84-Simulated-QKD')}</td></tr>
      <tr><td style="padding:6px 0;color:#5c6bc0;">Original Size</td><td style="padding:6px 0;text-align:right;">{original_length} chars</td></tr>
      <tr><td style="padding:6px 0;color:#5c6bc0;">Sent At</td><td style="padding:6px 0;text-align:right;">{timestamp}</td></tr>
    </table>
  </div>

  <!-- Encrypted Payload -->
  <div style="padding:20px 24px;background:rgba(10,10,25,0.95);border-left:1px solid rgba(0,229,255,0.15);border-right:1px solid rgba(0,229,255,0.15);">
    <p style="margin:0 0 12px;font-size:11px;color:#00e5ff;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;">🔒 Encrypted Payload</p>

    <p style="margin:0 0 4px;font-size:10px;color:#5c6bc0;text-transform:uppercase;letter-spacing:1px;">Nonce (Hex)</p>
    <div style="padding:10px 14px;background:rgba(0,0,0,0.4);border-radius:8px;border:1px solid rgba(99,110,180,0.15);margin-bottom:14px;">
      <code style="font-family:'Courier New',monospace;font-size:12px;color:#00e5ff;word-break:break-all;">{payload.get('nonce', 'N/A')}</code>
    </div>

    <p style="margin:0 0 4px;font-size:10px;color:#5c6bc0;text-transform:uppercase;letter-spacing:1px;">Ciphertext (Hex)</p>
    <div style="padding:10px 14px;background:rgba(0,0,0,0.4);border-radius:8px;border:1px solid rgba(99,110,180,0.15);margin-bottom:14px;">
      <code style="font-family:'Courier New',monospace;font-size:12px;color:#b388ff;word-break:break-all;">{payload.get('ciphertext', 'N/A')}</code>
    </div>

    <p style="margin:0 0 4px;font-size:10px;color:#5c6bc0;text-transform:uppercase;letter-spacing:1px;">HMAC-SHA256 Tag</p>
    <div style="padding:10px 14px;background:rgba(0,0,0,0.4);border-radius:8px;border:1px solid rgba(99,110,180,0.15);">
      <code style="font-family:'Courier New',monospace;font-size:12px;color:#ff9100;word-break:break-all;">{payload.get('hmac', 'N/A')}</code>
    </div>
  </div>

  <!-- Footer -->
  <div style="padding:20px 24px;background:rgba(15,15,35,0.8);border-radius:0 0 16px 16px;border:1px solid rgba(0,229,255,0.15);border-top:none;text-align:center;">
    <p style="margin:0 0 8px;font-size:12px;color:#5c6bc0;">
      To decrypt, use the shared quantum-derived key with the QSES decryption tool.
    </p>
    <p style="margin:0;font-size:10px;color:rgba(92,107,192,0.6);">
      ⚛️ QSES — Classical simulation of quantum key distribution. Not real QKD.
    </p>
  </div>

</div>
</body>
</html>"""

    def reload_config(self):
        """Re-read configuration from environment variables."""
        self._load_config()

