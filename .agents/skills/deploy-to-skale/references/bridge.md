# Bridge

## Token Bridge

```typescript
const token = new Contract(tokenAddress, ERC20_ABI, signer);
const bridge = new Contract(bridgeAddress, BRIDGE_ABI, signer);

await token.approve(bridgeAddress, amount);
await bridge.depositERC20(tokenAddress, amount, targetChain, receiver);
```

## IMA Messaging

MessageProxy: `0xd2AAa00100000000000000000000000000000000`

Reference: [IMA Docs](https://docs.skale.space/developers/skale-bridge/messaging-layer/message-proxy.md)
