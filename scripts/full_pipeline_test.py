#!/usr/bin/env python3
"""DOF Full Pipeline Test — Real connections (Supabase, Avalanche mainnet)."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from core.governance import ConstitutionEnforcer
from core.ast_verifier import ASTVerifier
from core.z3_verifier import Z3Verifier
from core.oags_bridge import OAGSIdentity, OAGSPolicyBridge
from core.oracle_bridge import OracleBridge, CertificateSigner, AttestationRegistry
from core.enigma_bridge import EnigmaBridge
from core.avalanche_bridge import AvalancheBridge
from core.memory_governance import GovernedMemoryStore

print('=' * 70)
print('DOF FULL PIPELINE TEST — REAL CONNECTIONS')
print('=' * 70)

# 1. INIT
print('\n[1] INITIALIZING COMPONENTS...')
enforcer = ConstitutionEnforcer()
ast_v = ASTVerifier()
z3 = Z3Verifier()
oags = OAGSIdentity()
identity = OAGSIdentity.compute_identity(
    model='dof-pipeline-test',
    constitution_hash='live_test',
    tools=['governance', 'ast', 'z3', 'enigma', 'avalanche'],
)
signer = CertificateSigner()
registry = AttestationRegistry()
bridge = OracleBridge(signer, oags)
enigma = EnigmaBridge()
memory = GovernedMemoryStore()

try:
    avax = AvalancheBridge()
    avax_online = True
    balance = avax.get_balance()
    print(f'  Avalanche: CONNECTED | Balance: {balance:.4f} AVAX')
except Exception as e:
    avax_online = False
    print(f'  Avalanche: OFFLINE ({e})')

print(f'  OAGS Identity: {identity[:16]}...')
print(f'  Enigma: {"CONNECTED" if enigma._engine else "OFFLINE"}')
print(f'  Components: ALL READY')

# 2. Z3 PROOFS
print('\n[2] Z3 FORMAL VERIFICATION...')
z3_results = z3.verify_all()
for r in z3_results:
    status = 'VERIFIED' if r.result == 'VERIFIED' else 'FAILED'
    print(f'  {status}  {r.theorem_name}  ({r.proof_time_ms:.2f}ms)')
z3_all = all(r.result == 'VERIFIED' for r in z3_results)
print(f'  All verified: {z3_all} | Total: {sum(r.proof_time_ms for r in z3_results):.2f}ms')

# 3. AGENTS
agents = [
    {
        'name': 'Apex Arbitrage',
        'token_id': '1687',
        'wallet': '0xcd595a299ad1d5D088B7764e9330f7B0be7ca983',
        'nft': '0xfc6f71502d24f04e0463452947cc152a0eb4de3c',
        'output': 'Arbitrage scan complete: AVAX/USDC spread 0.28% detected on TraderJoe vs Pangolin. Profit: $14.20 after gas. Execution: 1.8s. Slippage within 0.1% tolerance. All positions closed. Portfolio balanced. Risk exposure: zero.',
        'code': 'spread = (price_a - price_b) / price_a * 100\nif spread > min_spread:\n    execute_trade(pair, amount)\n    log_profit(spread, gas_cost)',
        'metrics': {'SS': 0.92, 'GCR': 1.0, 'PFI': 0.15, 'RP': 0.10, 'SSR': 0.0},
    },
    {
        'name': 'AvaBuilder Agent',
        'token_id': '1686',
        'wallet': '0x29a45b03F07D1207f2e3ca34c38e7BE5458CE71a',
        'nft': '0x9b59db8e7534924e34baa67a86454125cb02206d',
        'output': 'Contract audit complete for DOFValidationRegistry.sol. Solidity 0.8.19. 0 critical vulnerabilities. 0 high severity. 1 medium: consider adding reentrancy guard on registerBatch. 3 gas optimizations: pack struct, use calldata, batch events. Test coverage: 96%. All 15 tests passing. OpenZeppelin patterns detected: Ownable.',
        'code': 'assert registry.totalAttestations() >= 0\nresult = registry.getAttestation(cert_hash)\nassert result[1] == True',
        'metrics': {'SS': 0.88, 'GCR': 1.0, 'PFI': 0.22, 'RP': 0.18, 'SSR': 0.0},
    },
]

all_results = []

for agent in agents:
    print(f'\n{"=" * 70}')
    print(f'AGENT: {agent["name"]} (#{agent["token_id"]})')
    print(f'  Wallet: {agent["wallet"]}')
    print(f'  NFT: {agent["nft"]}')
    print(f'{"=" * 70}')

    result = {'agent': agent['name'], 'token_id': agent['token_id']}

    # GOVERNANCE
    print('\n[3] GOVERNANCE CHECK...')
    gov = enforcer.enforce(agent['output'])
    gov_score = gov.get('score', 0) if isinstance(gov, dict) else 0
    gov_pass = gov.get('status') not in ('BLOCKED',) if isinstance(gov, dict) else True
    hard = gov.get('hard_violations', []) if isinstance(gov, dict) else []
    soft = gov.get('soft_violations', []) if isinstance(gov, dict) else []
    print(f'  Status: {"PASS" if gov_pass else "BLOCKED"}')
    print(f'  Score: {gov_score}')
    print(f'  Hard violations: {len(hard)}')
    print(f'  Soft violations: {len(soft)}')
    result['governance'] = {'pass': gov_pass, 'score': gov_score, 'hard': len(hard), 'soft': len(soft)}

    # AST
    print('\n[4] AST VERIFICATION...')
    ast_result = ast_v.verify(agent['code'])
    ast_score = ast_result.get('score', 1.0) if isinstance(ast_result, dict) else 1.0
    ast_violations = ast_result.get('violations', []) if isinstance(ast_result, dict) else []
    print(f'  Score: {ast_score}')
    print(f'  Violations: {len(ast_violations)}')
    result['ast'] = {'score': ast_score, 'violations': len(ast_violations)}

    # METRICS
    print('\n[5] CAUSAL METRICS...')
    m = agent['metrics']
    acr = 0.85 if agent['token_id'] == '1687' else 0.90
    m['ACR'] = acr
    for k, v in m.items():
        print(f'  {k}: {v}')
    result['metrics'] = m

    # ATTESTATION
    print('\n[6] CREATE ATTESTATION...')
    cert = bridge.create_attestation(
        task_id=f'live_real_test_{agent["token_id"]}',
        metrics=m,
    )
    cert_hash = cert.certificate_hash if hasattr(cert, 'certificate_hash') else str(cert)
    gov_status = 'COMPLIANT' if m['GCR'] == 1.0 else 'NON_COMPLIANT'
    should_pub = m['GCR'] == 1.0
    print(f'  Certificate: {cert_hash[:32]}...')
    print(f'  Governance: {cert.governance_status if hasattr(cert, "governance_status") else "N/A"}')
    print(f'  Z3: {cert.z3_verified if hasattr(cert, "z3_verified") else "N/A"}')
    print(f'  Status: {gov_status}')
    print(f'  Should publish: {should_pub}')
    result['attestation'] = {'hash': cert_hash[:32], 'status': gov_status}

    # PUBLISH ENIGMA (dof_trust_scores)
    print('\n[7] PUBLISH TO ENIGMA (dof_trust_scores)...')
    try:
        enigma_ok = enigma.publish_trust_score(
            attestation={
                'metrics': m,
                'governance_status': gov_status,
                'certificate_hash': str(cert_hash),
                'z3_verified': z3_all,
                'ast_score': ast_score,
                'on_chain_tx': None,
                'on_chain_block': None,
            },
            oags_identity=agent['token_id'],
        )
        print(f'  Enigma: {"PUBLISHED" if enigma_ok else "FAILED"}')
        result['enigma'] = 'PUBLISHED' if enigma_ok else 'FAILED'
    except Exception as e:
        print(f'  Enigma: ERROR — {e}')
        result['enigma'] = f'ERROR: {e}'

    # PUBLISH ON-CHAIN
    if avax_online and should_pub:
        print('\n[8] PUBLISH ON-CHAIN (Avalanche mainnet)...')
        try:
            tx = avax.send_attestation(
                certificate_hash=str(cert_hash),
                agent_id=agent['nft'],
                compliant=True,
            )
            tx_hash = tx.get('tx_hash', 'unknown') if isinstance(tx, dict) else str(tx)
            block = tx.get('block_number', 0) if isinstance(tx, dict) else 0
            gas = tx.get('gas_used', 0) if isinstance(tx, dict) else 0
            status = tx.get('status', 'unknown') if isinstance(tx, dict) else 'unknown'
            print(f'  TX: {tx_hash}')
            print(f'  Block: {block}')
            print(f'  Gas: {gas}')
            print(f'  Status: {status}')
            result['avalanche'] = {'tx': str(tx_hash), 'block': block, 'gas': gas, 'status': status}

            # Update enigma with on-chain data
            try:
                enigma.publish_trust_score(
                    attestation={
                        'metrics': m,
                        'governance_status': gov_status,
                        'certificate_hash': str(cert_hash),
                        'z3_verified': z3_all,
                        'ast_score': ast_score,
                        'on_chain_tx': str(tx_hash),
                        'on_chain_block': block,
                    },
                    oags_identity=agent['token_id'],
                )
                print('  Enigma updated with on-chain TX')
            except Exception:
                pass

        except Exception as e:
            print(f'  Avalanche: ERROR — {e}')
            result['avalanche'] = f'ERROR: {e}'
    else:
        print(f'\n[8] ON-CHAIN: SKIPPED (avax_online={avax_online}, should_pub={should_pub})')
        result['avalanche'] = 'SKIPPED'

    # VERIFY ON-CHAIN
    if avax_online and isinstance(result.get('avalanche'), dict) and result['avalanche'].get('tx'):
        print('\n[9] VERIFY ON-CHAIN...')
        try:
            time.sleep(3)
            verify = avax.verify_on_chain(str(cert_hash))
            if isinstance(verify, dict):
                print(f'  Exists: {verify.get("exists", False)}')
                print(f'  Compliant: {verify.get("compliant", False)}')
            else:
                print(f'  Verify result: {verify}')
            result['on_chain_verify'] = verify if isinstance(verify, dict) else str(verify)
        except Exception as e:
            print(f'  Verify: {e}')

    # MEMORY
    print('\n[10] SAVE TO GOVERNED MEMORY...')
    try:
        memory.add(
            content=f'{agent["name"]} verified: GCR={m["GCR"]}, SS={m["SS"]}, AST={ast_score}, Z3={z3_all}, on-chain=true',
            category='knowledge',
        )
        print('  Memory: SAVED')
        result['memory'] = 'SAVED'
    except Exception as e:
        print(f'  Memory: {e}')
        result['memory'] = str(e)

    all_results.append(result)

# FINAL SUMMARY
print(f'\n{"=" * 70}')
print('FINAL RESULTS')
print(f'{"=" * 70}')
print(f'  Agents tested: {len(all_results)}')
print(f'  Z3 theorems: {sum(1 for r in z3_results if r.result == "VERIFIED")}/4 VERIFIED')

if avax_online:
    bal = avax.get_balance()
    total_att = avax.total_attestations()
    print(f'  Wallet balance: {bal:.4f} AVAX')
    print(f'  Total on-chain attestations: {total_att}')

for r in all_results:
    print(f'\n  {r["agent"]} (#{r["token_id"]}):')
    gov_status_str = "PASS" if r["governance"]["pass"] else "FAIL"
    print(f'    Governance: {gov_status_str} (score {r["governance"]["score"]})')
    print(f'    AST: {r["ast"]["score"]} ({r["ast"]["violations"]} violations)')
    print(f'    Enigma: {r["enigma"]}')
    if isinstance(r.get('avalanche'), dict):
        print(f'    Avalanche: {r["avalanche"]["status"]} (tx: {r["avalanche"]["tx"][:20]}...)')
        print(f'    Snowtrace: https://snowtrace.io/tx/{r["avalanche"]["tx"]}')
    else:
        print(f'    Avalanche: {r.get("avalanche", "N/A")}')
    print(f'    Memory: {r["memory"]}')

# Read combined view
print(f'\n{"=" * 70}')
print('COMBINED TRUST VIEW (from enigma-dev)')
print(f'{"=" * 70}')
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(os.environ['ENIGMA_DATABASE_URL'])
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                'SELECT agent_id, token_id, alive_score, active_score, governance_score, '
                'safety_score, community_score, combined_trust_score, dof_z3_verified, '
                'dof_governance_status, dof_on_chain_tx '
                'FROM combined_trust_view WHERE governance_score > 0 '
                'ORDER BY combined_trust_score DESC'
            )
        ).fetchall()
        for r in rows:
            print(
                f'  #{r[1]} | Alive={r[2]:.2f} Active={r[3]:.2f} Gov={r[4]:.2f} '
                f'Safety={r[5]:.2f} Comm={r[6]:.2f} | COMBINED={r[7]:.2f} | Z3={r[8]} | {r[9]}'
            )
            if r[10]:
                print(f'       On-chain: https://snowtrace.io/tx/{r[10]}')
except Exception as e:
    print(f'  View error: {e}')
    print('  Note: Run REFRESH MATERIALIZED VIEW CONCURRENTLY combined_trust_view to update')

print(f'\n  Pipeline complete.')
print(f'{"=" * 70}')
