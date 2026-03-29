// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol"; // Fix typo here

// Simple Paygate for Synthesis 2026 - Agents that Pay track
// This contract facilitates micropayments for DOF observability reports.
contract DOFPaygate is Ownable {
    IERC20 public paymentToken; // e.g., USDC or DOF Token
    uint256 public reportPrice; // Price per report in token units

    event PaymentReceived(address indexed user, uint256 amount, string reportId);
    event PriceUpdated(uint256 newPrice);

    constructor(address _paymentToken, uint256 _initialPrice) Ownable(msg.sender) {
        paymentToken = IERC20(_paymentToken);
        reportPrice = _initialPrice;
    }

    function setPrice(uint256 _newPrice) external onlyOwner {
        reportPrice = _newPrice;
        emit PriceUpdated(_newPrice);
    }

    /**
     * @dev Pay for access to a specific observability report.
     * @param reportId The identifier of the report being purchased.
     */
    function payForReport(string calldata reportId) external {
        require(paymentToken.transferFrom(msg.sender, address(this), reportPrice), "Payment failed");
        emit PaymentReceived(msg.sender, reportPrice, reportId);
    }

    function withdrawTokens() external onlyOwner {
        uint256 balance = paymentToken.balanceOf(address(this));
        require(paymentToken.transfer(owner(), balance), "Withdrawal failed");
    }
}
