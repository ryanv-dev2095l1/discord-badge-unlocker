import json
import time
import urllib.request
from typing import Any

API_BASE = "https://discord.com/api/v9"

# https://discord.com/developers/docs/resources/user#user-object-user-flags
BADGE_FLAGS = {
    1 << 0: "Staff",
    1 << 1: "Partner",
    1 << 2: "HypeSquad",
    1 << 3: "BugHunterLevel1",
    1 << 6: "HypeSquadBravery",
    1 << 7: "HypeSquadBrilliance",
    1 << 8: "HypeSquadBalance",
    1 << 9: "EarlySupporter",
    1 << 10: "TeamUser",
    1 << 14: "BugHunterLevel2",
    1 << 17: "VerifiedBot",
    1 << 18: "EarlyVerifiedBotDeveloper",
    1 << 19: "CertifiedModerator",
    1 << 20: "BotHTTPInteractions",
    1 << 21: "ActiveDeveloper",
}

ALL_BADGES = list(BADGE_FLAGS.values()) + ["NitroClassic", "NitroBoost", "NitroBasic", "QuestBadge"]

RATE_LIMIT_SECONDS = 5

class BadTokenError(Exception):
    pass

def _request(path: str, token: str) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise BadTokenError()
        if e.code == 429:
            retry_after = RATE_LIMIT_SECONDS
            try:
                retry_after = int(e.headers.get("Retry-After", RATE_LIMIT_SECONDS))
            except (ValueError, TypeError):
                pass
            time.sleep(retry_after)
            return _request(path, token)
        raise

def _parse_badges(flags: int) -> list[str]:
    badges = []
    for bit, name in BADGE_FLAGS.items():
        if flags & bit:
            badges.append(name)
    return badges

def fetch_user(token: str) -> dict[str, Any]:
    data = _request("/users/@me", token)
    badges = _parse_badges(data.get("public_flags", 0))

    nitro_type = None
    if data.get("premium_type") == 1:
        nitro_type = "NitroClassic"
    elif data.get("premium_type") == 2:
        nitro_type = "NitroBoost"
    elif data.get("premium_type") == 3:
        nitro_type = "NitroBasic"

    if nitro_type:
        badges.append(nitro_type)

    # Avatar decoration implies active nitro in most cases
    if data.get("avatar_decoration_data") and not nitro_type:
        badges.append("NitroBoost")

    # Quest badges not yet exposed in public_flags, check collectibles
    # TODO: quest badges moved to /users/@me/collectibles in 2024, migrate when stable
    if data.get("collectibles"):
        for c in data["collectibles"]:
            if c.get("type") == "QUEST" and "QuestBadge" not in badges:
                badges.append("QuestBadge")

    # New username system: discriminator is "0" or absent
    discriminator = data.get("discriminator", "0")
    if discriminator == "0":
        display_name = data["username"]
    else:
        display_name = f"{data['username']}#{discriminator}"

    return {
        "id": data["id"],
        "username": data["username"],
        "discriminator": discriminator,
        "display_name": display_name,
        "public_flags": data.get("public_flags", 0),
        "badges": badges,
    }
