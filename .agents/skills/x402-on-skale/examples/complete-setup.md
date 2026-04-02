# x402 on SKALE Examples

## Complete Server Setup with Hono

```typescript
// server.ts
import { Hono } from "hono";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";

const app = new Hono();

// Initialize x402 with PayAI facilitator
const client = new HTTPFacilitatorClient({ 
    url: "https://facilitator.payai.network" 
});
const server = new x402ResourceServer(client);
server.register("eip155:*", new ExactEvmScheme());

// Configure payment-protected endpoints
app.use(paymentMiddleware({
    "GET /api/data": {
        accepts: [{
            scheme: "exact",
            network: "eip155:324705682", // SKALE Base Sepolia
            payTo: "0xYourReceivingAddress",
            price: { 
                amount: "1000",  // 0.001 USDC
                asset: "0x2e08028E3C4c2356572E096d8EF835cD5C6030bD"
            }
        }]
    },
    "POST /api/analyze": {
        accepts: [{
            scheme: "exact",
            network: "eip155:324705682",
            payTo: "0xYourReceivingAddress",
            price: { 
                amount: "10000",  // 0.01 USDC
                asset: "0x2e08028E3C4c2356572E096d8EF835cD5C6030bD"
            }
        }]
    }
}, server));

// Protected endpoints
app.get("/api/data", (c) => {
    return c.json({ 
        data: "Premium data content",
        timestamp: Date.now()
    });
});

app.post("/api/analyze", async (c) => {
    const body = await c.req.json();
    // Perform analysis...
    return c.json({ 
        result: "Analysis complete",
        input: body
    });
});

export default app;
```

## Complete Agent Client

```typescript
// client.ts
import { x402Client, x402HTTPClient } from "@x402/core/client";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${string}`);

const httpClient = new x402HTTPClient(
    new x402Client().register("eip155:*", new ExactEvmScheme(account))
);

export async function fetchPaidResource(url: string, options?: RequestInit) {
    // First attempt - may get 402
    const response = await fetch(url, options);
    
    if (response.status === 402) {
        console.log("Payment required, processing...");
        
        const responseBody = await response.json();
        const paymentRequired = httpClient.getPaymentRequiredResponse(
            (name) => response.headers.get(name),
            responseBody
        );
        
        // Create and encode payment
        const paymentPayload = await httpClient.createPaymentPayload(paymentRequired);
        const paymentHeaders = httpClient.encodePaymentSignatureHeader(paymentPayload);
        
        // Retry with payment
        const paidResponse = await fetch(url, {
            ...options,
            headers: {
                ...options?.headers,
                ...paymentHeaders
            }
        });
        
        if (!paidResponse.ok) {
            throw new Error(`Payment failed: ${paidResponse.status}`);
        }
        
        return paidResponse.json();
    }
    
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    
    return response.json();
}

// Usage
async function main() {
    try {
        const data = await fetchPaidResource("https://api.example.com/api/data");
        console.log("Received:", data);
    } catch (error) {
        console.error("Failed:", error);
    }
}
```

## Package.json Dependencies

```json
{
  "dependencies": {
    "@x402/core": "latest",
    "@x402/evm": "latest",
    "@x402/hono": "latest",
    "hono": "latest",
    "viem": "latest"
  }
}
```

## Environment Variables

```bash
# .env
PRIVATE_KEY=0x...  # Agent wallet private key
SERVER_URL=https://facilitator.payai.network
RECEIVING_ADDRESS=0x...  # Where payments go
```
