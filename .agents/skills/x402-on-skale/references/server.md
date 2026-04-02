# Server

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
