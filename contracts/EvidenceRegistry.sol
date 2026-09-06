// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract EvidenceRegistry {
    struct Attestation {
        uint64 timestamp;
        address submitter;
        bool exists;
    }

    mapping(bytes32 => Attestation) public attestations;

    event EvidenceAttested(bytes32 indexed evidenceHash, address indexed submitter, uint64 timestamp);

    function attest(bytes32 evidenceHash) external {
        require(evidenceHash != bytes32(0), "empty hash");
        require(!attestations[evidenceHash].exists, "already attested");

        uint64 nowTs = uint64(block.timestamp);
        attestations[evidenceHash] = Attestation(nowTs, msg.sender, true);
        emit EvidenceAttested(evidenceHash, msg.sender, nowTs);
    }

    function verify(bytes32 evidenceHash) external view returns (bool, uint64, address) {
        Attestation memory item = attestations[evidenceHash];
        return (item.exists, item.timestamp, item.submitter);
    }
}
