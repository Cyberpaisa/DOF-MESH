---
name: x402-on-skale
description: Build AI agents with x402 payments on SKALE. Covers facilitator setup, payment middleware, and agent client. Use for monetized AI services, agent-to-agent payments.
---

# x402 on SKALE

x402 is HTTP 402 protocol for AI agent payments. Zero gas fees make SKALE ideal for micropayments.

## What is x402?

- Extends HTTP with native payment capabilities using `402 Payment Required`
- Paywalled Resources: Protect APIs behind payments
- Autonomous Payments: Agents automatically pay for resources
- ERC-3009 Compatibility: Uses TransferWithAuthorization for gasless payments

## Facilitators

Use a facilitator to handle payments - don't run your own:

| Service | URL | Notes |
|---------|-----|-------|
| PayAI | `https://facilitator.payai.network` | Recommended |
| Corbits | `https://corbits.dev` | Developer-focused |
| RelAI | `https://api.relai.fi` | Marketplace |
| Kobaru | `https://kobaru.io` | Enterprise |

## Payment Tokens on SKALE

| Token | Address | Decimals |
|-------|---------|----------|
| Bridged USDC | `0x2e08028E3C4c2356572E096d8EF835cD5C6030bD` | 6 |
| Axios USD | `0x61a26022927096f444994dA1e53F0FD9487EAfcf` | 6 |

## Network IDs

Format: `eip155:CHAIN_ID`

| Chain | Chain ID | x402 Network ID |
|-------|----------|-----------------|
| SKALE Base Sepolia | 324705682 | `eip155:324705682` |
| SKALE Base | 1187947933 | `eip155:1187947933` |

## Install

```bash
npm install @x402/core @x402/evm @x402/hono
```

## Server Setup

```typescript
import { Hono } from "hono";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";

const client = new HTTPFacilitatorClient({ url: "https://facilitator.payai.network" });
const server = new x402ResourceServer(client);
server.register("eip155:*", new ExactEvmScheme());

const app = new Hono();

app.use(paymentMiddleware({
    "GET /api/premium": {
        accepts: [{
            scheme: "exact",
            network: "eip155:324705682",
            payTo: "0xYourReceivingAddress",
            price: { 
                amount: "10000",  // 0.01 USDC (6 decimals)
                asset: "0x2e08028E3C4c2356572E096d8EF835cD5C6030bD"
            }
        }]
    }
}, server));

app.get("/api/premium", (c) => c.json({ data: "premium!" }));
```

### Multiple Endpoints

```typescript
app.use(paymentMiddleware({
    "GET /api/basic": {
        accepts: [{
            scheme: "exact",
            network: "eip155:324705682",
            payTo: "0xYourAddress",
            price: { amount: "1000", asset: "0x..." }  // 0.001 USDC
        }]
    },
    "GET /api/premium": {
        accepts: [{
            scheme: "exact",
            network: "eip155:324705682",
            payTo: "0xYourAddress",
            price: { amount: "10000", asset: "0x..." }  // 0.01 USDC
        }]
    }
}, server));
```

## Agent Client

```typescript
import { x402Client, x402HTTPClient } from "@x402/core/client";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${string}`);
const httpClient = new x402HTTPClient(
    new x402Client().register("eip155:*", new ExactEvmScheme(account))
);

async function accessPaidResource(url: string) {
    const response = await fetch(url);
    
    if (response.status === 402) {
        const responseBody = await response.json();
        const paymentRequired = httpClient.getPaymentRequiredResponse(
            (name) => response.headers.get(name),
            responseBody
        );
        
        const paymentPayload = await httpClient.createPaymentPayload(paymentRequired);
        const paymentHeaders = httpClient.encodePaymentSignatureHeader(paymentPayload);
        
        const paidResponse = await fetch(url, { headers: paymentHeaders });
        return paidResponse.json();
    }
    
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    
    return response.json();
}
```

## Price Calculation

Amount is in token decimals (USDC = 6):

| Amount | USDC |
|--------|------|
| 100 | $0.0001 |
| 1000 | $0.001 |
| 10000 | $0.01 |
| 1000000 | $1.00 |

## Use Cases

- **Autonomous Service Access**: Agents pay for API calls, data feeds, AI services
- **Monetize Agent Services**: Protect AI endpoints with payments
- **Multi-Agent Economies**: Agent-to-agent payments for services

Reference: [x402 Docs](https://docs.skale.space/get-started/agentic-builders/start-with-x402.md)
