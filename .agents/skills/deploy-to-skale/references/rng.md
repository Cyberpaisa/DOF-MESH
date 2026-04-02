# RNG

Native random via precompile at `0x18`.

## Library

```solidity
import "@dirtroad/skale-rng/contracts/RNG.sol";

contract MyContract is RNG {
    function random() external view returns (uint256) {
        return getRandomNumber();
    }
    
    function randomRange(uint256 min, uint256 max) external view returns (uint256) {
        return getNextRandomRange(min, max);
    }
}
```

Install: `forge install dirtroad/skale-rng`

## Notes

- RNG is native to SKALE (relies on SKALE Consensus)
- On local testing or other chains, returns 0
- Multiple calls in same block return same value

Reference: [RNG Docs](https://docs.skale.space/cookbook/native-features/rng-get-random-number.md)
