# Common Command Flows

## Read Contract Method

```bash
skale read <contract> <method> [params...] --chain <chain>
skale read <contract> <method> [params...] --network <network>
```

## Whitelist Check

```bash
skale whitelist <address> --chain <chain>
```

## Manager Status

```bash
skale manager version --chain <chain>
skale manager mtm-status --chain <chain>
skale manager fcd-status --chain <chain>
```

## IMA Queries

```bash
skale ima chain-id --chain <chain>
skale ima connected-chains --chain <chain>
skale ima chain-id --network <network>
skale ima connected-chains --network <network>
```

## SKL Token Queries

```bash
skale skl info --network mainnet
skale skl balance <address> --network mainnet
```
