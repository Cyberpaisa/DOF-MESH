# Command Matrix

Authoritative source: `~/projects/skale-cli/src` (commands, chains, contracts).

## Targets

### SKALE chains (`--chain`)

- `calypso`
- `europa`
- `nebula`
- `titan`
- `strayshot`
- `calypso-testnet`
- `europa-testnet`
- `nebula-testnet`
- `titan-testnet`

### Ethereum networks (`--network`)

- `mainnet`
- `holesky`

## Contract Support by Target

### SKALE target (`--chain`)

- `configController`
- `messageProxyForSchain`
- `tokenManagerERC20`

### Ethereum target (`--network`)

- `messageProxy`
- `sklToken`

## Command Playbooks

### read

```bash
skale read <contract> <method> [params...] --chain <chain>
skale read <contract> <method> [params...] --network <network>
```

Validation and behavior:
- Require a target selector: `--chain` or `--network`.
- Current source validates that at least one target is present. If both are supplied, the implementation currently follows the `--chain` path.
- Reject unsupported contract per target.
- Reject unknown method on selected contract.
- Parameter coercion:
- `"true"`/`"false"` -> boolean
- decimal integer string -> BigInt
- `0x`-prefixed value -> hex string passthrough
- all others -> string

### whitelist

```bash
skale whitelist <address> --chain <chain>
```

Validation and behavior:
- Validate Ethereum address format.
- Calls `configController.isAddressWhitelisted(address)`.

### manager

```bash
skale manager version --chain <chain>
skale manager mtm-status --chain <chain>
skale manager fcd-status --chain <chain>
```

Behavior:
- Uses `configController` on selected chain.
- Returns version/boolean status fields.

### ima

```bash
skale ima chain-id --chain <chain>
skale ima chain-id --network <network>
skale ima connected-chains --chain <chain>
skale ima connected-chains --network <network>
```

Behavior:
- SKALE path uses `messageProxyForSchain`.
- Ethereum path uses `messageProxy`.

### skl

```bash
skale skl info --network mainnet
skale skl balance <address> --network mainnet
```

Behavior:
- Uses ERC20 ABI against `sklToken` contract.
- Balance output includes raw value and formatted value.

## Error Taxonomy

- `MISSING_TARGET`: `--chain` or `--network` not provided where required.
- `INVALID_ADDRESS`: input is not a valid Ethereum address.
- `INVALID_CONTRACT`: contract not supported for selected target.
- `INVALID_METHOD`: method does not exist on selected contract.
- `CALL_FAILED`: RPC/contract call execution failed.

## Notes

- Keep examples command-first and concise.
- Do not invent additional commands not present in source.
