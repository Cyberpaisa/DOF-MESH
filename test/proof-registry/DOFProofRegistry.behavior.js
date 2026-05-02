const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DOFProofRegistry behavior", function () {
  async function deployRegistry() {
    const Registry = await ethers.getContractFactory("DOFProofRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();
    return registry;
  }

  function transcriptBytes(text) {
    return ethers.toUtf8Bytes(text);
  }

  function transcriptHash(text) {
    return ethers.keccak256(transcriptBytes(text));
  }

  it("registerProof stores a proof record and increments proof count", async function () {
    const registry = await deployRegistry();

    const agentId = 1687n;
    const trustScore = ethers.parseEther("0.95");
    const transcript = "z3 proof transcript: invariant set A";
    const z3ProofHash = transcriptHash(transcript);
    const storageRef = "ipfs://proof-record-1687";
    const invariantsCount = 8;

    expect(await registry.getProofCount()).to.equal(0n);

    await expect(
      registry.registerProof(
        agentId,
        trustScore,
        z3ProofHash,
        storageRef,
        invariantsCount
      )
    )
      .to.emit(registry, "ProofRegistered")
      .withArgs(0n, agentId, z3ProofHash, storageRef);

    expect(await registry.getProofCount()).to.equal(1n);

    const record = await registry.getProof(0);

    expect(record.agentId).to.equal(agentId);
    expect(record.trustScore).to.equal(trustScore);
    expect(record.z3ProofHash).to.equal(z3ProofHash);
    expect(record.storageRef).to.equal(storageRef);
    expect(record.invariantsCount).to.equal(invariantsCount);
    expect(record.verified).to.equal(false);
  });

  it("verifyProof marks a proof as verified when transcript hash matches", async function () {
    const registry = await deployRegistry();

    const transcript = "z3 proof transcript: valid";
    const z3ProofHash = transcriptHash(transcript);

    await registry.registerProof(
      1687n,
      ethers.parseEther("1"),
      z3ProofHash,
      "local://valid-proof",
      8
    );

    expect(
      await registry.verifyProof.staticCall(0, transcriptBytes(transcript))
    ).to.equal(true);

    await expect(registry.verifyProof(0, transcriptBytes(transcript)))
      .to.emit(registry, "ProofVerified")
      .withArgs(0n, true);

    const record = await registry.getProof(0);
    expect(record.verified).to.equal(true);
  });

  it("verifyProof rejects an invalid transcript and leaves proof unverified", async function () {
    const registry = await deployRegistry();

    const validTranscript = "z3 proof transcript: valid";
    const invalidTranscript = "z3 proof transcript: tampered";
    const z3ProofHash = transcriptHash(validTranscript);

    await registry.registerProof(
      1687n,
      ethers.parseEther("1"),
      z3ProofHash,
      "local://tamper-test",
      8
    );

    expect(
      await registry.verifyProof.staticCall(0, transcriptBytes(invalidTranscript))
    ).to.equal(false);

    await registry.verifyProof(0, transcriptBytes(invalidTranscript));

    const record = await registry.getProof(0);
    expect(record.verified).to.equal(false);
  });

  it("getProof reverts for invalid proof IDs", async function () {
    const registry = await deployRegistry();

    await expect(registry.getProof(0)).to.be.revertedWith(
      "DOFProofRegistry: invalid proof ID"
    );
  });
});

describe("DOFEvaluator proof lookup behavior", function () {
  async function deployRegistryAndEvaluator() {
    const Registry = await ethers.getContractFactory("DOFProofRegistry");
    const registry = await Registry.deploy();
    await registry.waitForDeployment();

    const Evaluator = await ethers.getContractFactory("DOFEvaluator");
    const evaluator = await Evaluator.deploy(await registry.getAddress());
    await evaluator.waitForDeployment();

    return { registry, evaluator };
  }

  function transcriptBytes(text) {
    return ethers.toUtf8Bytes(text);
  }

  function transcriptHash(text) {
    return ethers.keccak256(transcriptBytes(text));
  }

  it("returns true when a matching proof hash exists and is verified", async function () {
    const { registry, evaluator } = await deployRegistryAndEvaluator();

    const transcript = "z3 proof transcript: evaluator accepted";
    const proofHash = transcriptHash(transcript);

    await registry.registerProof(
      1687n,
      ethers.parseEther("0.99"),
      proofHash,
      "local://evaluator-valid",
      8
    );

    await registry.verifyProof(0, transcriptBytes(transcript));

    expect(await evaluator.verifyProof(proofHash)).to.equal(true);
  });

  it("returns false when a matching proof hash exists but is not verified", async function () {
    const { registry, evaluator } = await deployRegistryAndEvaluator();

    const transcript = "z3 proof transcript: evaluator unverified";
    const proofHash = transcriptHash(transcript);

    await registry.registerProof(
      1687n,
      ethers.parseEther("0.99"),
      proofHash,
      "local://evaluator-unverified",
      8
    );

    expect(await evaluator.verifyProof(proofHash)).to.equal(false);
  });

  it("returns false when no matching proof hash exists", async function () {
    const { evaluator } = await deployRegistryAndEvaluator();

    const unknownProofHash = transcriptHash("unknown z3 proof transcript");

    expect(await evaluator.verifyProof(unknownProofHash)).to.equal(false);
  });
});
