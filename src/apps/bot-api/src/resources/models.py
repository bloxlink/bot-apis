import copy
from dataclasses import dataclass, field

from resources.constants import DEFAULTS

__all__ = (
    "UserData",
    "GuildData",
    "RobloxAccount",
)


def default_field(obj):
    return field(default_factory=lambda: copy.copy(obj))


@dataclass(slots=True)
class UserData:
    id: int
    robloxID: str = None
    robloxAccounts: dict = default_field({"accounts": [], "guilds": {}})


@dataclass(slots=True)
class GuildData:
    id: int
    binds: list = default_field([])  # FIXME

    verifiedRoleEnabled: bool = True
    verifiedRoleName: str = "Verified"  # deprecated
    verifiedRole: str = None

    unverifiedRoleEnabled: bool = True
    unverifiedRoleName: str = "Unverified"  # deprecated
    unverifiedRole: str = None

    nicknameTemplate: str = DEFAULTS.get("nicknameTemplate")
    unverifiedNickname: str = None
    allowOldRoles: bool = False

    # Old bind fields.
    roleBinds: dict = None
    groupIDs: dict = None
    converted_binds: bool = False
