# CTX Solidity

Install: `forge install skalenetwork/bite-solidity`

```solidity
pragma solidity >=0.8.27;

import { BITE } from "@skalenetwork/bite-solidity/BITE.sol";
import { IBiteSupplicant } from "@skalenetwork/bite-solidity/interfaces/IBiteSupplicant.sol";

contract Secret is IBiteSupplicant {
    bytes public message;
    
    function reveal(bytes calldata encrypted) external payable {
        BITE.submitCTX(
            BITE.SUBMIT_CTX_ADDRESS,
            msg.value / tx.gasprice,
            encrypted,
            new bytes[](0)
        );
    }
    
    function onDecrypt(bytes[] calldata decrypted, bytes[] calldata) external override {
        message = decrypted[0];
    }
}
```

## Requirements

- Solidity >=0.8.27
- EVM istanbul

```toml
solc_version = "0.8.27"
evm_version = "istanbul"
```

Reference: [CTX Docs](https://docs.skale.space/developers/bite-protocol/conditional-transactions.md)
