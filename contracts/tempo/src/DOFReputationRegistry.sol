// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DOFReputationRegistry {
    struct Feedback {
        address from;
        address to;
        uint8 score; // 0-100
        string comment;
        uint256 timestamp;
    }

    mapping(address => Feedback[]) public feedbacks;
    mapping(address => uint256) public averageScore;
    mapping(address => uint256) public feedbackCount;

    event FeedbackGiven(address indexed from, address indexed to, uint8 score, string comment);

    function giveFeedback(address to, uint8 score, string calldata comment) external {
        require(score <= 100, "Score max 100");
        require(msg.sender != to, "Cannot self-rate");

        feedbacks[to].push(Feedback(msg.sender, to, score, comment, block.timestamp));

        uint256 count = feedbackCount[to] + 1;
        averageScore[to] = ((averageScore[to] * feedbackCount[to]) + score) / count;
        feedbackCount[to] = count;

        emit FeedbackGiven(msg.sender, to, score, comment);
    }

    function getAverageScore(address agent) external view returns (uint256) {
        return averageScore[agent];
    }

    function getFeedbackCount(address agent) external view returns (uint256) {
        return feedbackCount[agent];
    }

    function getLatestFeedback(address agent, uint256 count) external view returns (Feedback[] memory) {
        Feedback[] storage all = feedbacks[agent];
        uint256 start = all.length > count ? all.length - count : 0;
        uint256 resultLen = all.length - start;
        Feedback[] memory result = new Feedback[](resultLen);
        for (uint256 i = 0; i < resultLen; i++) {
            result[i] = all[start + i];
        }
        return result;
    }
}
