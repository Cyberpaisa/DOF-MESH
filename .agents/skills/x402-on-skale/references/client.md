# Agent Client

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
    
    return response.json();
}
```
