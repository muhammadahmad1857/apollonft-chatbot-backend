def fetch_user_details(user_id: str) -> dict:
    """Fetch details for a user by ID.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        A dictionary with user details including name and wallet address.
    """
    # Stub — wire to real DB/API later
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "wallet": "0x0000000000000000000000000000000000000000",
        "joined": "2024-01-01",
        "nfts_owned": 0,
    }
