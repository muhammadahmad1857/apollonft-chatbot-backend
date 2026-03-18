"""
ApolloNFT Agent Behavior Test
Run: python -X utf8 test.py
Make sure the backend is running: uvicorn app.main:app --reload
"""
import asyncio
import httpx
import json
import sys

import time as _time

BASE_URL = "http://localhost:8000"
STEP_DELAY = 4.0   # seconds between chat turns (avoids Gemini rate limits)
TEST_DELAY = 6.0   # seconds between test cases
# Unique prefix per run so sessions never reuse old history
RUN_ID = str(int(_time.time()))[-6:]  # last 6 digits of unix timestamp


async def chat(client: httpx.AsyncClient, message: str, session_id: str) -> str:
    """Send a chat message and return the full assistant response."""
    full_text = ""
    async with client.stream(
        "POST",
        f"{BASE_URL}/api/chat",
        json={"session_id": session_id, "message": message},
        timeout=90,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            raw = line[6:]
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue  # skip [DONE] or malformed lines
            full_text += payload.get("text", "")
            if payload.get("done"):
                break
    return full_text.strip()


def section(title: str):
    print(f"\n{'='*62}")
    print(f"  {title}")
    print("=" * 62)


def show(user: str, agent: str):
    print(f"\n  User : {user}")
    agent_preview = agent[:300] + "..." if len(agent) > 300 else agent
    print(f"  Agent: {agent_preview}")
    if "[ACTION:" in agent:
        for ln in agent.split("\n"):
            if "[ACTION:" in ln:
                print(f"    --> {ln.strip()}")


def ok(msg: str):   print(f"  [PASS] {msg}")
def fail(msg: str): print(f"  [FAIL] {msg}")
def warn(msg: str): print(f"  [WARN] {msg}")


# ─── Test Cases ───────────────────────────────────────────────────────────────

async def test_mint_flow(client: httpx.AsyncClient):
    """T1: Natural mint conversation — agent collects info then calls upload_mint."""
    section("T1: Natural Mint Flow")
    s = f"{RUN_ID}-t1"
    r1 = await chat(client, "I want to mint an NFT", s)
    show("I want to mint an NFT", r1)
    await asyncio.sleep(STEP_DELAY)

    r2 = await chat(client, "Call it Solar Drift, description: ambient soundscape, royalty 5%", s)
    show("Call it Solar Drift, description: ambient soundscape, royalty 5%", r2)

    if "[ACTION:upload_mint:" in r2:
        ok("Agent called upload_mint with collected data")
        if "500" in r2 or "royalty_bps" in r2:
            ok("Royalty 500 bps present")
    else:
        fail("Expected [ACTION:upload_mint:...]")


async def test_files_staged_before_agent_asks(client: httpx.AsyncClient):
    """T2: User attaches files before agent asks — agent must NOT ask to attach again."""
    section("T2: Files Staged Before Agent Asks")
    s = f"{RUN_ID}-t2"
    r1 = await chat(client, "I want to mint this NFT (I've attached: cover.png, track.mp3)", s)
    show("I've attached: cover.png, track.mp3", r1)
    await asyncio.sleep(STEP_DELAY)

    r2 = await chat(client, "Name it Digital Dreamscape, royalty 5%", s)
    show("Name it Digital Dreamscape, royalty 5%", r2)

    if "[ACTION:upload_mint:" in r2:
        ok("Agent called upload_mint immediately (files were staged)")
        if "attach" in r2.lower() and "again" in r2.lower():
            warn("Agent asked to attach again — should not")
    else:
        fail("Expected [ACTION:upload_mint:...] — agent should not ask to attach again")


async def test_agent_suggests_name(client: httpx.AsyncClient):
    """T3: Agent suggests a creative name when asked."""
    section("T3: Agent Suggests Name")
    s = f"{RUN_ID}-t3"
    r1 = await chat(client, "Mint this image with 5% royalty. You suggest the name.", s)
    show("Mint this image with 5% royalty. You suggest the name.", r1)

    has_suggestion = any(w in r1.lower() for w in ["how about", "suggest", "name it", "call it", '"', "'"])
    if has_suggestion:
        ok("Agent suggested a name")
    else:
        warn("No clear name suggestion detected")

    await asyncio.sleep(STEP_DELAY)
    r2 = await chat(client, "Yes, go with that name", s)
    show("Yes, go with that name", r2)

    if "[ACTION:upload_mint:" in r2:
        ok("Agent called upload_mint after confirmation")
    else:
        fail("Expected [ACTION:upload_mint:...] — agent must call the tool, not just say 'underway'")


async def test_marketplace_listing(client: httpx.AsyncClient):
    """T4: List NFT on marketplace with explicit token ID."""
    section("T4: Marketplace Listing")
    s = f"{RUN_ID}-t4"
    r1 = await chat(client, "List token ID 42 on the marketplace for 0.5 ETH", s)
    show("List token ID 42 on the marketplace for 0.5 ETH", r1)

    if "[ACTION:list_marketplace:" in r1:
        ok("Agent called list_marketplace")
        if "42" in r1:
            ok("Token ID 42 present in action")
        else:
            warn("Token ID 42 not found — check manually")
    else:
        fail("Expected [ACTION:list_marketplace:...]")


async def test_auction(client: httpx.AsyncClient):
    """T5: Start an auction."""
    section("T5: Auction")
    s = f"{RUN_ID}-t5"
    r1 = await chat(client, "Start an auction for NFT #7, minimum bid 0.1 ETH, 48 hours", s)
    show("Start an auction for NFT #7, minimum bid 0.1 ETH, 48 hours", r1)

    if "[ACTION:list_auction:" in r1:
        ok("Agent called list_auction")
        if "48" in r1:
            ok("Duration 48h present")
    else:
        fail("Expected [ACTION:list_auction:...]")


async def test_existing_token_uri(client: httpx.AsyncClient):
    """T6: Mint from an existing IPFS URI."""
    section("T6: Mint from Existing Token URI")
    s = f"{RUN_ID}-t6"
    r1 = await chat(client, "Mint this URI for me: ipfs://QmXyz123abc, royalty 2.5%", s)
    show("Mint ipfs://QmXyz123abc, royalty 2.5%", r1)

    if "[ACTION:mint_nft:" in r1:
        ok("Agent called mint_nft with token URI")
    else:
        fail("Expected [ACTION:mint_nft:...]")


async def test_post_mint_list(client: httpx.AsyncClient):
    """T7a: After mint success message, 'list it' uses token ID 99."""
    section("T7a: Post-Mint -> List on Marketplace")
    s = f"{RUN_ID}-t7a"
    confirm = (
        'My NFT "Solar Drift" was successfully minted on-chain. '
        'Token ID: 99. Transaction: 0xdeadbeef. '
        'Please remember Token ID 99 — I may want to list it on the marketplace or start an auction next.'
    )
    r1 = await chat(client, confirm, s)
    show("(mint success message)", r1)
    await asyncio.sleep(STEP_DELAY)

    r2 = await chat(client, "Now list it on the marketplace for 1 ETH", s)
    show("Now list it on the marketplace for 1 ETH", r2)

    if "[ACTION:list_marketplace:" in r2:
        if "99" in r2:
            ok("Agent remembered Token ID 99 and listed it")
        else:
            warn("list_marketplace triggered but token_id may be wrong — check manually")
    else:
        fail("Expected [ACTION:list_marketplace:...] using Token ID 99")


async def test_post_mint_auction(client: httpx.AsyncClient):
    """T7b: After mint success message, 'auction it' uses token ID 99."""
    section("T7b: Post-Mint -> Auction")
    s = f"{RUN_ID}-t7b"
    confirm = (
        'My NFT "Solar Drift" was successfully minted on-chain. '
        'Token ID: 99. Transaction: 0xdeadbeef. '
        'Please remember Token ID 99 — I may want to list it on the marketplace or start an auction next.'
    )
    r1 = await chat(client, confirm, s)
    show("(mint success message)", r1)
    await asyncio.sleep(STEP_DELAY)

    r2 = await chat(client, "Start an auction for it, minimum bid 0.5 ETH", s)
    show("Start an auction for it, minimum bid 0.5 ETH", r2)

    if "[ACTION:list_auction:" in r2:
        if "99" in r2:
            ok("Agent remembered Token ID 99 for auction")
        else:
            warn("list_auction triggered but token_id may be wrong — check manually")
    else:
        fail("Expected [ACTION:list_auction:...] using Token ID 99")


async def test_knowledge_base(client: httpx.AsyncClient):
    """T8: General platform knowledge."""
    section("T8: Platform Knowledge")
    s = f"{RUN_ID}-t8"
    r1 = await chat(client, "What is ApolloNFT and what can I do here?", s)
    show("What is ApolloNFT?", r1)
    if r1:
        ok("Got a response")
    else:
        fail("Empty response from agent")


# ─── Runner ───────────────────────────────────────────────────────────────────

async def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\nApolloNFT Agent Test Suite")
    print(f"Backend: {BASE_URL}\n")

    try:
        async with httpx.AsyncClient() as client:
            hc = await client.get(f"{BASE_URL}/health", timeout=5)
            hc.raise_for_status()
        print("[OK] Backend is up")
    except Exception as e:
        print(f"[ERR] Backend not reachable: {e}")
        print("Start it: uvicorn app.main:app --reload")
        sys.exit(1)

    tests = [
        test_mint_flow,
        test_files_staged_before_agent_asks,
        test_agent_suggests_name,
        test_marketplace_listing,
        test_auction,
        test_existing_token_uri,
        test_post_mint_list,
        test_post_mint_auction,
        test_knowledge_base,
    ]

    async with httpx.AsyncClient() as client:
        for i, test_fn in enumerate(tests):
            if i > 0:
                await asyncio.sleep(TEST_DELAY)
            try:
                await test_fn(client)
            except httpx.HTTPStatusError as e:
                print(f"\n[ERR] HTTP {e.response.status_code} in {test_fn.__name__}: {e}")
            except Exception as e:
                print(f"\n[ERR] Exception in {test_fn.__name__}: {type(e).__name__}: {e}")

    print(f"\n{'='*62}")
    print("  Done. Review [PASS] / [FAIL] / [WARN] above.")
    print("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
