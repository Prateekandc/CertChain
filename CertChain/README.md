# CertChain

**Blockchain-Based Certificate Verification System**

Stack: Python · Solidity · Web3.py · Flask · Ethereum (Sepolia)

## Project Overview

CertChain is a decentralized certificate verification platform that eliminates certificate fraud by storing SHA-256 hashes of academic documents on the Ethereum blockchain. Institutions issue certificates by storing their cryptographic fingerprint on-chain; anyone can verify a certificate's authenticity in seconds without needing to contact the institution.

**Key insight:** only the hash is stored on-chain (not the actual PDF), which keeps gas costs minimal while still making the certificate tamper-proof. If a single byte of the original document changes, the hash changes — making forgery immediately detectable.

## How It Works

### Issuing a Certificate
1. University uploads the signed PDF to the backend
2. Backend computes SHA-256 hash of the PDF bytes
3. Backend calls `issueCertificate()` on the smart contract with the hash + metadata
4. Ethereum transaction confirmed → hash is now permanently on-chain

### Verifying a Certificate
1. Verifier uploads the certificate PDF (or provides the hash)
2. System computes SHA-256 of the uploaded file
3. Calls `verifyCertificate()` on the smart contract — read-only, no gas cost
4. Returns: valid/invalid + recipient name, course, institution, and timestamp

## Setup & Installation

### 1. Install dependencies
```bash
# Python dependencies
pip install flask web3 python-dotenv flask-cors

# Install Ganache for local blockchain (dev)
npm install -g ganache

# Install Solidity compiler
pip install py-solc-x
```

### 2. Configure environment
Copy `.env.example` to `.env` and fill in your own values:
```bash
cp .env.example .env
```
```
RPC_URL=http://127.0.0.1:8545
CONTRACT_ADDRESS=0xYourDeployedContractAddress
PRIVATE_KEY=0xYourWalletPrivateKey
```
> ⚠️ Never commit your real `.env` file — it's already excluded via `.gitignore`.

### 3. Compile & deploy the smart contract
```bash
# Start local blockchain
ganache --deterministic

# Compile contract (generates build/CertificateVerifier.abi)
solc --abi --bin CertificateVerifier.sol -o build/

# Deploy (use Remix IDE or a deploy script)
# Copy the deployed address into .env → CONTRACT_ADDRESS
```

### 4. Run the backend
```bash
python app.py
# API now running at http://localhost:5000
```

## API Reference

| Method | Endpoint    | Description                              |
|--------|-------------|-------------------------------------------|
| GET    | `/health`   | Health check                              |
| POST   | `/hash`     | Compute SHA-256 hash of an uploaded file  |
| POST   | `/issue`    | Issue a new certificate on-chain          |
| POST   | `/verify`   | Verify a certificate against the chain    |
| POST   | `/revoke`   | Revoke a previously issued certificate    |
| GET    | `/total`    | Get total number of certificates issued   |

## Deploying to Testnet (Sepolia)
```bash
# Get test ETH from: https://sepoliafaucet.com

# Update .env
RPC_URL=https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID

# Deploy using Remix IDE:
# 1. Open https://remix.ethereum.org
# 2. Paste CertificateVerifier.sol
# 3. Compile with Solidity 0.8.19
# 4. Deploy via Injected Provider (MetaMask on Sepolia)
# 5. Copy contract address → .env CONTRACT_ADDRESS
```

## Technologies Used
Python · Flask · Solidity · Web3.py · Ethereum · Ganache · Sepolia Testnet · SHA-256 · Smart Contracts · REST API · Blockchain · MetaMask

## Project Structure
```
CertChain/
├── app.py                     # Flask backend API
├── CertificateVerifier.sol    # Solidity smart contract
├── CertificateVerifier.abi    # Compiled contract ABI
├── build/
│   └── CertificateVerifier.abi
├── index.html                 # Frontend UI
├── uploads/                   # Runtime file uploads (gitignored)
├── .env.example                # Environment variable template
└── requirements.txt
```

---
Built with Python · Solidity · Web3.py
