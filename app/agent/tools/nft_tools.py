import json


def request_nft_upload(name: str, description: str = "", royalty_bps: int = 0) -> str:
    """Initiate the full NFT minting flow for user-owned files (cover image + music track).

    Use this whenever the user wants to mint a NEW NFT from their own files.
    The frontend will show an upload card so the user can provide their files,
    then it will automatically upload to IPFS and mint — no extra steps needed.

    Args:
        name: Name for the NFT.
        description: Description of the NFT.
        royalty_bps: Royalty in basis points (0–1000, max 10%).

    Returns:
        An ACTION marker the frontend handles.
    """
    if royalty_bps < 0 or royalty_bps > 1000:
        return "Error: royalty_bps must be between 0 and 1000 (max 10%)."
    payload = json.dumps({"name": name, "description": description, "royalty_bps": royalty_bps})
    return f"[ACTION:upload_mint:{payload}]"


def fetch_nft_metadata(contract_address: str, token_id: str) -> dict:
    """Fetch NFT metadata from on-chain or an indexer.

    Args:
        contract_address: The ERC-721/1155 contract address.
        token_id: The token ID within the contract.

    Returns:
        A dictionary with NFT metadata including name, description, and image.
    """
    # Stub — wire to Alchemy/Moralis later
    return {
        "contract": contract_address,
        "token_id": token_id,
        "name": f"NFT #{token_id}",
        "description": "A unique digital asset on the ApolloNFT platform.",
        "image": "https://placeholder.apollonft.io/nft.png",
        "attributes": [],
    }


def mint_nft(token_uri: str, royalty_bps: int = 0) -> str:
    """Mint a new NFT on the ApolloNFT contract.

    The frontend will execute the actual blockchain transaction and confirm
    back to the backend via POST /api/nft/confirm.

    Args:
        token_uri: The metadata URI for the NFT (IPFS or HTTPS).
        royalty_bps: Royalty in basis points (100 = 1%). Max 1000 (10%).

    Returns:
        An ACTION marker that the frontend will execute.
    """
    if royalty_bps < 0 or royalty_bps > 1000:
        return "Error: royalty_bps must be between 0 and 1000 (max 10%)."
    payload = json.dumps({"token_uri": token_uri, "royalty_bps": royalty_bps})
    return f"[ACTION:mint_nft:{payload}]"


def list_nft_marketplace(token_id: int, price_eth: str) -> str:
    """List an owned NFT on the ApolloNFT marketplace.

    The frontend will approve the marketplace contract then call list().
    Confirm back via POST /api/nft/confirm with status='marketplace'.

    Args:
        token_id: The token ID to list.
        price_eth: Listing price in ETH (e.g. "0.5").

    Returns:
        An ACTION marker that the frontend will execute.
    """
    try:
        float(price_eth)
    except (ValueError, TypeError):
        return "Error: price_eth must be a valid number (e.g. '0.5')."
    payload = json.dumps({"token_id": token_id, "price_eth": str(price_eth)})
    return f"[ACTION:list_marketplace:{payload}]"


def delist_nft_marketplace(token_id: int) -> str:
    """Delist (cancel) an NFT listing from the ApolloNFT marketplace.

    The frontend will call cancel() on the marketplace contract.
    Confirm back via POST /api/nft/confirm with status='owned'.

    Args:
        token_id: The token ID to delist.

    Returns:
        An ACTION marker that the frontend will execute.
    """
    payload = json.dumps({"token_id": token_id})
    return f"[ACTION:delist_marketplace:{payload}]"


def get_user_portfolio(wallet_address: str = "") -> str:
    """Show the user's NFT portfolio in the chat.

    Call this when the user asks to see their NFTs, collection, or portfolio.
    The frontend will fetch and display all their NFTs inline.

    Args:
        wallet_address: The user's wallet address. Leave empty if unknown — the
                        frontend will use the connected wallet automatically.

    Returns:
        A PORTFOLIO marker that the frontend renders as an NFT grid.
    """
    payload = json.dumps({"wallet": wallet_address})
    return f"[PORTFOLIO:{payload}]"


def buy_nft_marketplace(token_id: int) -> str:
    """Buy an NFT that is listed on the ApolloNFT marketplace.

    The frontend will read the listing price, ask the user to confirm, then
    call buy() on the marketplace contract. Ownership is transferred on-chain.

    Args:
        token_id: The token ID to purchase.

    Returns:
        An ACTION marker that the frontend will execute.
    """
    payload = json.dumps({"token_id": token_id})
    return f"[ACTION:buy_marketplace:{payload}]"


def request_batch_mint(collection_name: str, royalty_bps: int = 0) -> str:
    """Batch-mint multiple staged files as a collection.

    Each file becomes its own NFT named "Collection Name #1", "#2", etc.
    The user must have already attached the files.

    Args:
        collection_name: Name prefix for the collection.
        royalty_bps: Royalty in basis points 0–1000 (max 10%). Default 0.

    Returns:
        An ACTION marker the frontend handles.
    """
    if royalty_bps < 0 or royalty_bps > 1000:
        return "Error: royalty_bps must be between 0 and 1000 (max 10%)."
    payload = json.dumps({"collection_name": collection_name, "royalty_bps": royalty_bps})
    return f"[ACTION:batch_mint:{payload}]"


def list_nft_auction(token_id: int, min_bid_eth: str, duration_hours: int = 24) -> str:
    """List an owned NFT on the ApolloNFT auction contract.

    An NFT can only be on auction OR marketplace at one time, not both.
    The frontend will approve the auction contract then call createAuction().
    Confirm back via POST /api/nft/confirm with status='auction'.

    Args:
        token_id: The token ID to auction.
        min_bid_eth: Minimum bid in ETH (e.g. "0.1").
        duration_hours: Auction duration in hours (default 24).

    Returns:
        An ACTION marker that the frontend will execute.
    """
    try:
        float(min_bid_eth)
    except (ValueError, TypeError):
        return "Error: min_bid_eth must be a valid number (e.g. '0.1')."
    if duration_hours < 1:
        return "Error: duration_hours must be at least 1."
    payload = json.dumps({
        "token_id": token_id,
        "min_bid_eth": str(min_bid_eth),
        "duration_hours": duration_hours,
    })
    return f"[ACTION:list_auction:{payload}]"
