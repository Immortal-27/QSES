"""
Quantum Key Distribution (BB84 Protocol) — Classical Simulation

DISCLAIMER: This is a classical simulation of the BB84 quantum key distribution
protocol. Real QKD requires dedicated quantum hardware and optical channels.
This simulation uses Python's `secrets` module for cryptographically secure
random number generation to faithfully model the protocol's behavior.

The BB84 protocol (Bennett & Brassard, 1984):
1. Alice generates random bits and encodes them in random bases (rectilinear or diagonal)
2. Alice sends qubits to Bob through a quantum channel
3. Bob measures each qubit using a randomly chosen basis
4. Alice and Bob publicly compare bases (not bit values) — keep only matching-basis bits
5. They sacrifice a portion of the sifted key to estimate the error rate
6. If error rate < threshold (~11%), the channel is secure; otherwise, Eve is present
"""

import secrets
from dataclasses import dataclass, field
from typing import List, Optional


# Basis symbols for visualization
RECTILINEAR = "+"  # measures |0⟩, |1⟩
DIAGONAL = "×"     # measures |+⟩, |-⟩

# Qubit state representations for the UI
QUBIT_STATES = {
    (0, "+"): "|0⟩",   # bit 0, rectilinear basis → vertical polarization
    (1, "+"): "|1⟩",   # bit 1, rectilinear basis → horizontal polarization
    (0, "×"): "|+⟩",   # bit 0, diagonal basis → +45° polarization
    (1, "×"): "|-⟩",   # bit 1, diagonal basis → -45° polarization
}


@dataclass
class BB84Result:
    """Complete result of a BB84 key exchange simulation."""
    n_qubits: int
    alice_bits: List[int]
    alice_bases: List[str]
    bob_bases: List[str]
    bob_measured_bits: List[int]
    matching_indices: List[int]
    sifted_key_alice: List[int]
    sifted_key_bob: List[int]
    sample_indices: List[int]
    sample_alice: List[int]
    sample_bob: List[int]
    error_rate: float
    final_key_bits: List[int]
    final_key_hex: str
    eavesdropper_present: bool
    eve_bases: Optional[List[str]] = None
    eve_measured_bits: Optional[List[int]] = None
    channel_secure: bool = True
    protocol_steps: List[dict] = field(default_factory=list)


def generate_random_bits(n: int) -> List[int]:
    """Generate n cryptographically secure random bits."""
    return [secrets.randbelow(2) for _ in range(n)]


def generate_random_bases(n: int) -> List[str]:
    """Generate n random basis choices (rectilinear '+' or diagonal '×')."""
    return [RECTILINEAR if secrets.randbelow(2) == 0 else DIAGONAL for _ in range(n)]


def measure_qubit(bit: int, send_basis: str, recv_basis: str) -> int:
    """
    Simulate quantum measurement of a qubit.

    If the receiver's basis matches the sender's, the measurement is deterministic.
    If bases differ, the result is random (50/50) — this is key to quantum security.
    """
    if send_basis == recv_basis:
        return bit  # Correct measurement
    else:
        return secrets.randbelow(2)  # Random outcome when bases mismatch


def simulate_eavesdropper(bits: List[int], sender_bases: List[str]) -> tuple:
    """
    Simulate Eve intercepting qubits on the quantum channel.

    Eve must measure each qubit (collapsing its state) and re-send it.
    She chooses random bases, so ~50% of the time she uses the wrong basis,
    which introduces errors that Alice and Bob can detect.

    Returns:
        eve_bases: Eve's randomly chosen bases
        eve_bits: Eve's measurement results
        forwarded_bits: Bits as re-sent to Bob (Eve's measured values)
    """
    eve_bases = generate_random_bases(len(bits))
    eve_bits = []

    for i in range(len(bits)):
        measured = measure_qubit(bits[i], sender_bases[i], eve_bases[i])
        eve_bits.append(measured)

    # Eve re-sends her measured values (she can't clone the original qubits)
    return eve_bases, eve_bits, eve_bits


def sift_key(alice_bits: List[int], bob_bits: List[int],
             alice_bases: List[str], bob_bases: List[str]) -> tuple:
    """
    Key sifting: keep only the bits where Alice and Bob used the same basis.

    Returns:
        matching_indices: indices where bases matched
        sifted_alice: Alice's sifted key bits
        sifted_bob: Bob's sifted key bits
    """
    matching_indices = []
    sifted_alice = []
    sifted_bob = []

    for i in range(len(alice_bits)):
        if alice_bases[i] == bob_bases[i]:
            matching_indices.append(i)
            sifted_alice.append(alice_bits[i])
            sifted_bob.append(bob_bits[i])

    return matching_indices, sifted_alice, sifted_bob


def estimate_error_rate(alice_sample: List[int], bob_sample: List[int]) -> float:
    """
    Compare a sample of sifted key bits to estimate the quantum bit error rate (QBER).

    In a perfect channel without eavesdropping: QBER ≈ 0%
    With an eavesdropper (intercept-resend attack): QBER ≈ 25%
    BB84 security threshold: QBER < 11%
    """
    if not alice_sample:
        return 0.0
    errors = sum(1 for a, b in zip(alice_sample, bob_sample) if a != b)
    return errors / len(alice_sample)


def bits_to_hex(bits: List[int]) -> str:
    """Convert a list of bits to a hexadecimal string."""
    if not bits:
        return ""
    # Pad to multiple of 8
    padded = bits + [0] * ((8 - len(bits) % 8) % 8)
    hex_str = ""
    for i in range(0, len(padded), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | padded[i + j]
        hex_str += f"{byte:02x}"
    return hex_str


def full_bb84_exchange(n_qubits: int = 256,
                       with_eavesdropper: bool = False) -> BB84Result:
    """
    Execute a complete BB84 quantum key distribution simulation.

    Args:
        n_qubits: Number of qubits to transmit (more = longer key, more reliable error estimation)
        with_eavesdropper: If True, simulate Eve performing an intercept-resend attack

    Returns:
        BB84Result with complete protocol details for visualization
    """
    steps = []

    # Step 1: Alice prepares qubits
    alice_bits = generate_random_bits(n_qubits)
    alice_bases = generate_random_bases(n_qubits)
    steps.append({
        "step": 1,
        "title": "Alice Prepares Qubits",
        "description": f"Alice generates {n_qubits} random bits and encodes each in a randomly chosen basis (+ or ×).",
        "detail": f"First 16 bits: {alice_bits[:16]}, bases: {alice_bases[:16]}"
    })

    # Step 2: Quantum transmission (with possible eavesdropping)
    eve_bases = None
    eve_bits = None
    transmitted_bits = alice_bits  # What Bob actually receives

    if with_eavesdropper:
        eve_bases, eve_bits, transmitted_bits = simulate_eavesdropper(
            alice_bits, alice_bases
        )
        steps.append({
            "step": 2,
            "title": "⚠️ Eve Intercepts the Quantum Channel",
            "description": "Eve measures each qubit with a random basis, collapsing the quantum state. "
                          "She re-sends her measured values to Bob. ~50% of the time she uses the wrong basis, "
                          "introducing undetectable-to-her errors.",
            "detail": f"Eve's bases: {eve_bases[:16]}"
        })
    else:
        steps.append({
            "step": 2,
            "title": "Quantum Channel Transmission",
            "description": "Alice sends qubits to Bob through the quantum channel. "
                          "No eavesdropper is present — qubits arrive undisturbed.",
            "detail": "Channel is secure"
        })

    # Step 3: Bob measures
    bob_bases = generate_random_bases(n_qubits)
    bob_measured_bits = []
    for i in range(n_qubits):
        # Bob measures the transmitted bits (which may have been altered by Eve)
        if with_eavesdropper:
            # Bob measures Eve's re-sent qubits
            measured = measure_qubit(transmitted_bits[i], eve_bases[i], bob_bases[i])
        else:
            measured = measure_qubit(alice_bits[i], alice_bases[i], bob_bases[i])
        bob_measured_bits.append(measured)

    steps.append({
        "step": 3,
        "title": "Bob Measures Qubits",
        "description": f"Bob independently chooses random bases and measures each qubit.",
        "detail": f"Bob's bases: {bob_bases[:16]}, measured: {bob_measured_bits[:16]}"
    })

    # Step 4: Basis reconciliation (public classical channel)
    matching_indices, sifted_alice, sifted_bob = sift_key(
        alice_bits, bob_measured_bits, alice_bases, bob_bases
    )
    steps.append({
        "step": 4,
        "title": "Basis Reconciliation",
        "description": f"Alice and Bob publicly compare bases (not values). "
                      f"They keep {len(matching_indices)} bits where bases matched "
                      f"({len(matching_indices)*100//n_qubits}% of transmitted qubits).",
        "detail": f"Matching indices (first 16): {matching_indices[:16]}"
    })

    # Step 5: Error rate estimation
    # Use ~25% of sifted key for error checking
    sample_size = max(1, len(sifted_alice) // 4)
    sample_indices = sorted(secrets.choice(range(len(sifted_alice)))
                           for _ in range(min(sample_size, len(sifted_alice))))
    # Deduplicate
    sample_indices = sorted(set(sample_indices))

    sample_alice = [sifted_alice[i] for i in sample_indices]
    sample_bob = [sifted_bob[i] for i in sample_indices]
    error_rate = estimate_error_rate(sample_alice, sample_bob)

    # Security threshold: 11% QBER
    channel_secure = error_rate < 0.11

    steps.append({
        "step": 5,
        "title": "Error Rate Estimation (Eavesdropping Detection)",
        "description": f"Alice and Bob sacrifice {len(sample_indices)} bits to estimate the error rate. "
                      f"QBER = {error_rate*100:.1f}%. "
                      f"{'✅ Below 11% threshold — channel is SECURE.' if channel_secure else '🚨 Above 11% threshold — EAVESDROPPER DETECTED!'}",
        "detail": f"Errors: {sum(1 for a, b in zip(sample_alice, sample_bob) if a != b)}/{len(sample_indices)}"
    })

    # Step 6: Final key (remaining sifted bits after removing samples)
    remaining_indices = [i for i in range(len(sifted_alice)) if i not in set(sample_indices)]
    final_key = [sifted_alice[i] for i in remaining_indices]

    # Truncate to 256 bits for AES-256 key
    if len(final_key) > 256:
        final_key = final_key[:256]

    final_key_hex = bits_to_hex(final_key)

    steps.append({
        "step": 6,
        "title": "Final Shared Key",
        "description": f"Remaining {len(final_key)} sifted bits form the shared secret key. "
                      f"{'Key is TRUSTED.' if channel_secure else 'Key is COMPROMISED — parties should abort.'}",
        "detail": f"Key (hex): {final_key_hex[:32]}..."
    })

    return BB84Result(
        n_qubits=n_qubits,
        alice_bits=alice_bits,
        alice_bases=alice_bases,
        bob_bases=bob_bases,
        bob_measured_bits=bob_measured_bits,
        matching_indices=matching_indices,
        sifted_key_alice=sifted_alice,
        sifted_key_bob=sifted_bob,
        sample_indices=sample_indices,
        sample_alice=sample_alice,
        sample_bob=sample_bob,
        error_rate=error_rate,
        final_key_bits=final_key,
        final_key_hex=final_key_hex,
        eavesdropper_present=with_eavesdropper,
        eve_bases=eve_bases,
        eve_measured_bits=eve_bits,
        channel_secure=channel_secure,
        protocol_steps=steps,
    )
