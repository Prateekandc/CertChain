"""
CertChain Backend — app.py
Flask API for hashing certificates and interacting with the smart contract.

Install dependencies:
    pip install flask web3 python-dotenv flask-cors

Run:
    python app.py
"""

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# Config — set these in a .env file
# ─────────────────────────────────────────────────────────────────────────────

RPC_URL          = os.getenv("RPC_URL", "http://127.0.0.1:8545")   # Ganache local
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
PRIVATE_KEY      = os.getenv("PRIVATE_KEY", "")                    # Issuer wallet key
UPLOAD_FOLDER    = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Load ABI (compile contract with: solc --abi CertificateVerifier.sol -o build/)
ABI_PATH = Path("build/CertificateVerifier.abi")

# ─────────────────────────────────────────────────────────────────────────────
# Web3 Setup
# ─────────────────────────────────────────────────────────────────────────────

w3 = Web3(Web3.HTTPProvider(RPC_URL))

def get_contract():
    """Load and return the deployed smart contract instance."""
    if not CONTRACT_ADDRESS:
        raise RuntimeError("CONTRACT_ADDRESS not set in .env")
    if not ABI_PATH.exists():
        raise FileNotFoundError(f"ABI not found at {ABI_PATH}. Compile the contract first.")
    abi = json.loads(ABI_PATH.read_text())
    return w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=abi
    )

# ─────────────────────────────────────────────────────────────────────────────
# Core Utilities
# ─────────────────────────────────────────────────────────────────────────────

def hash_file(file_path: Path) -> str:
    """Compute SHA-256 hash of a file. Returns lowercase hex string."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def hex_to_bytes32(hex_str: str) -> bytes:
    """Convert a 64-char hex hash to bytes32 for the smart contract."""
    return bytes.fromhex(hex_str)

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Check API and blockchain connection status."""
    connected = w3.is_connected()
    return jsonify({
        "status":      "ok",
        "blockchain":  "connected" if connected else "disconnected",
        "chain_id":    w3.eth.chain_id if connected else None,
        "block":       w3.eth.block_number if connected else None,
    })


@app.route("/hash", methods=["POST"])
def compute_hash():
    """
    Upload a certificate file and get its SHA-256 hash.
    Does NOT write to blockchain — just hashing.

    Request: multipart/form-data with field 'file'
    Response: { hash: "abc123...", filename: "cert.pdf" }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Save temporarily to compute hash
    tmp_path = UPLOAD_FOLDER / file.filename
    file.save(tmp_path)

    cert_hash = hash_file(tmp_path)
    tmp_path.unlink()  # Delete after hashing — we only store the hash

    return jsonify({
        "hash":     cert_hash,
        "filename": file.filename,
        "algorithm": "SHA-256"
    })


@app.route("/issue", methods=["POST"])
def issue_certificate():
    """
    Issue a certificate by storing its hash on the blockchain.

    Request JSON:
        {
            "hash":      "abc123...",   # SHA-256 hex string
            "recipient": "Arjun Sharma",
            "course":    "B.Tech CSE",
            "authority": "IIT Delhi"
        }

    Response:
        { "tx_hash": "0x...", "block": 42, "gas_used": 123456 }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["hash", "recipient", "course", "authority"]
    for field in required:
        if field not in data or not data[field].strip():
            return jsonify({"error": f"Missing field: {field}"}), 400

    if len(data["hash"]) != 64:
        return jsonify({"error": "Invalid SHA-256 hash (must be 64 hex chars)"}), 400

    if not PRIVATE_KEY:
        return jsonify({"error": "PRIVATE_KEY not set in .env"}), 500

    try:
        contract  = get_contract()
        account   = w3.eth.account.from_key(PRIVATE_KEY)
        cert_hash = hex_to_bytes32(data["hash"])

        txn = contract.functions.issueCertificate(
            cert_hash,
            data["recipient"].strip(),
            data["course"].strip(),
            data["authority"].strip()
        ).build_transaction({
            "from":     account.address,
            "nonce":    w3.eth.get_transaction_count(account.address),
            "gas":      300_000,
            "gasPrice": w3.eth.gas_price,
        })

        signed = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return jsonify({
            "success":  True,
            "tx_hash":  tx_hash.hex(),
            "block":    receipt.blockNumber,
            "gas_used": receipt.gasUsed,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/verify", methods=["POST"])
def verify_certificate():
    """
    Verify a certificate by its hash OR by uploading the file.

    Option A — JSON body:
        { "hash": "abc123..." }

    Option B — multipart/form-data:
        file field (will be hashed server-side)

    Response:
        {
            "valid":      true,
            "hash":       "abc123...",
            "recipient":  "Arjun Sharma",
            "course":     "B.Tech CSE",
            "authority":  "IIT Delhi",
            "issued_at":  "2024-01-15T10:30:00",
        }
    """
    cert_hash_hex = None

    # Option A: hash provided directly
    if request.is_json:
        data = request.get_json()
        cert_hash_hex = data.get("hash", "")

    # Option B: file upload
    elif "file" in request.files:
        file = request.files["file"]
        tmp_path = UPLOAD_FOLDER / file.filename
        file.save(tmp_path)
        cert_hash_hex = hash_file(tmp_path)
        tmp_path.unlink()

    if not cert_hash_hex or len(cert_hash_hex) != 64:
        return jsonify({"error": "Provide a valid 64-char SHA-256 hash or upload a file"}), 400

    try:
        contract  = get_contract()
        cert_hash = hex_to_bytes32(cert_hash_hex)

        valid, recipient, course, authority, issued_at = \
            contract.functions.verifyCertificate(cert_hash).call()

        result = {
            "valid": valid,
            "hash":  cert_hash_hex,
        }

        if valid:
            result.update({
                "recipient":  recipient,
                "course":     course,
                "authority":  authority,
                "issued_at":  datetime.utcfromtimestamp(issued_at).isoformat(),
            })
        else:
            result["reason"] = "Certificate not found or has been revoked"

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/revoke", methods=["POST"])
def revoke_certificate():
    """
    Revoke a certificate (admin only).

    Request JSON: { "hash": "abc123..." }
    """
    data = request.get_json()
    if not data or "hash" not in data:
        return jsonify({"error": "hash required"}), 400

    try:
        contract  = get_contract()
        account   = w3.eth.account.from_key(PRIVATE_KEY)
        cert_hash = hex_to_bytes32(data["hash"])

        txn = contract.functions.revokeCertificate(cert_hash).build_transaction({
            "from":     account.address,
            "nonce":    w3.eth.get_transaction_count(account.address),
            "gas":      100_000,
            "gasPrice": w3.eth.gas_price,
        })

        signed  = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return jsonify({
            "success":  True,
            "tx_hash":  tx_hash.hex(),
            "block":    receipt.blockNumber,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/total", methods=["GET"])
def total_certificates():
    """Return total number of certificates issued."""
    try:
        contract = get_contract()
        total    = contract.functions.totalCertificates().call()
        return jsonify({"total": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("CertChain API starting...")
    print(f"  RPC:      {RPC_URL}")
    print(f"  Contract: {CONTRACT_ADDRESS or 'NOT SET'}")
    app.run(debug=True, port=5000)
