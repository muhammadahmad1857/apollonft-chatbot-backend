import json


def request_wallet_connect(reason: str = "To access your NFT portfolio") -> str:
    """Request the user to connect their crypto wallet.

    Use this when the user asks about their owned NFTs, wallet balance,
    or any action that requires wallet access.

    Args:
        reason: Brief explanation of why wallet access is needed.

    Returns:
        A client action marker that renders as a Connect Wallet button in the UI.
    """
    return f'[ACTION:connect_wallet:{json.dumps({"reason": reason})}]'
