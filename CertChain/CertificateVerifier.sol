// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title CertChain - Blockchain Certificate Verification System
/// @author Your Name
/// @notice Stores and verifies SHA-256 hashes of certificates on-chain

contract CertificateVerifier {

    // ─────────────────────────────────────────────
    // Structs & State
    // ─────────────────────────────────────────────

    struct Certificate {
        string  recipientName;
        string  courseName;
        string  issuingAuthority;
        uint256 issuedAt;        // Unix timestamp
        address issuedBy;        // Wallet that issued it
        bool    exists;
        bool    revoked;
    }

    // certHash (bytes32) → Certificate
    mapping(bytes32 => Certificate) private certificates;

    // Track all hashes ever issued (for enumeration)
    bytes32[] public allHashes;

    // Only authorized issuers can register certificates
    mapping(address => bool) public authorizedIssuers;
    address public owner;

    // ─────────────────────────────────────────────
    // Events
    // ─────────────────────────────────────────────

    event CertificateIssued(
        bytes32 indexed certHash,
        string  recipientName,
        string  courseName,
        string  issuingAuthority,
        uint256 issuedAt,
        address issuedBy
    );

    event CertificateRevoked(bytes32 indexed certHash, address revokedBy);
    event IssuerAdded(address indexed issuer);
    event IssuerRemoved(address indexed issuer);

    // ─────────────────────────────────────────────
    // Modifiers
    // ─────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "Not contract owner");
        _;
    }

    modifier onlyIssuer() {
        require(
            authorizedIssuers[msg.sender] || msg.sender == owner,
            "Not an authorized issuer"
        );
        _;
    }

    // ─────────────────────────────────────────────
    // Constructor
    // ─────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
        authorizedIssuers[msg.sender] = true;
    }

    // ─────────────────────────────────────────────
    // Core Functions
    // ─────────────────────────────────────────────

    /// @notice Issue a new certificate by storing its SHA-256 hash
    /// @param certHash  SHA-256 hash of the certificate PDF (as bytes32)
    /// @param recipient Full name of the certificate recipient
    /// @param course    Course or degree name
    /// @param authority Name of the institution issuing the certificate
    function issueCertificate(
        bytes32 certHash,
        string  calldata recipient,
        string  calldata course,
        string  calldata authority
    ) external onlyIssuer {
        require(!certificates[certHash].exists, "Certificate already registered");
        require(bytes(recipient).length > 0,    "Recipient name required");
        require(bytes(course).length > 0,       "Course name required");
        require(bytes(authority).length > 0,    "Issuing authority required");

        certificates[certHash] = Certificate({
            recipientName:    recipient,
            courseName:       course,
            issuingAuthority: authority,
            issuedAt:         block.timestamp,
            issuedBy:         msg.sender,
            exists:           true,
            revoked:          false
        });

        allHashes.push(certHash);

        emit CertificateIssued(
            certHash, recipient, course, authority,
            block.timestamp, msg.sender
        );
    }

    /// @notice Verify whether a certificate hash is valid and not revoked
    /// @param certHash SHA-256 hash of the certificate PDF
    /// @return valid       True if registered and not revoked
    /// @return recipient   Recipient's name
    /// @return course      Course/degree name
    /// @return authority   Issuing institution
    /// @return issuedAt    Unix timestamp of issuance
    function verifyCertificate(bytes32 certHash)
        external
        view
        returns (
            bool    valid,
            string  memory recipient,
            string  memory course,
            string  memory authority,
            uint256 issuedAt
        )
    {
        Certificate storage cert = certificates[certHash];
        if (!cert.exists || cert.revoked) {
            return (false, "", "", "", 0);
        }
        return (
            true,
            cert.recipientName,
            cert.courseName,
            cert.issuingAuthority,
            cert.issuedAt
        );
    }

    /// @notice Revoke a certificate (marks it invalid without deleting history)
    function revokeCertificate(bytes32 certHash) external onlyIssuer {
        require(certificates[certHash].exists,  "Certificate not found");
        require(!certificates[certHash].revoked, "Already revoked");
        certificates[certHash].revoked = true;
        emit CertificateRevoked(certHash, msg.sender);
    }

    // ─────────────────────────────────────────────
    // Admin Functions
    // ─────────────────────────────────────────────

    function addIssuer(address issuer) external onlyOwner {
        authorizedIssuers[issuer] = true;
        emit IssuerAdded(issuer);
    }

    function removeIssuer(address issuer) external onlyOwner {
        authorizedIssuers[issuer] = false;
        emit IssuerRemoved(issuer);
    }

    function totalCertificates() external view returns (uint256) {
        return allHashes.length;
    }
}
