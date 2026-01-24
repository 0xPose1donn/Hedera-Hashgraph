function listNFT(
    address token,
    int64[] calldata serials,
    uint256 pricePerNFT,
    address royaltyRecipient,
    uint96 royaltyBps,
    address paymentToken,
    string calldata fullMetadataURI
) external {
    require(serials.length > 0, "No serials");
    require(pricePerNFT > 0, "Invalid price");
    require(royaltyBps <= 2000, "Royalty too high");

    // Track original seller
    for (uint256 i = 0; i < serials.length; i++) {
        if (originalSellerOf[token][serials[i]] == address(0)) {
            originalSellerOf[token][serials[i]] = msg.sender;
        }
    }

    // Build NFT transfers
    IHederaTokenService.NftTransfer[] memory nftTransfers =
        new IHederaTokenService.NftTransfer[](serials.length);

    for (uint256 i = 0; i < serials.length; i++) {
        nftTransfers[i] = IHederaTokenService.NftTransfer({
            senderAccountID: msg.sender,
            receiverAccountID: address(this),
            serialNumber: serials[i]
        });
    }

    // Token transfer list
    IHederaTokenService.TokenTransferList[] memory tokenTransfers =
        new IHederaTokenService.TokenTransferList;

    tokenTransfers[0] = IHederaTokenService.TokenTransferList({
        token: token,
        transfers: new IHederaTokenService.AccountAmount,
        nftTransfers: nftTransfers
    });

    // Execute transfer (requires prior approval)
    int64 response = hts.cryptoTransfer(tokenTransfers);
    require(response == 22, "NFT transfer failed");

    totalListings++;

    listings[totalListings] = Listing({
        seller: msg.sender,
        tokenAddress: token,
        serials: serials,
        pricePerNFT: pricePerNFT,
        active: true,
        royalty: RoyaltyInfo(
            originalSellerOf[token][serials[0]],
            msg.sender,
            royaltyRecipient,
            royaltyBps
        ),
        paymentToken: paymentToken,
        fullMetadataURI: fullMetadataURI
    });

    emit NFTListed(totalListings, msg.sender, token, serials, pricePerNFT);
}
