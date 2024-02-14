import copy

from attrs import define, field

from resources.constants import DEFAULTS

__all__ = (
    "UserData",
    "GuildData",
)


def default_field(obj):
    return field(factory=lambda: copy.copy(obj))


@define(slots=True)
class UserData:
    id: int
    robloxID: str = None
    robloxAccounts: dict = default_field({"accounts": [], "guilds": {}})


@define(slots=True)
class GuildData:
    """Representation of the stored settings for a guild"""

    id: int
    binds: list = default_field([])  # FIXME

    verifiedRoleEnabled: bool = True
    verifiedRoleName: str = "Verified"  # deprecated
    verifiedRole: str = None

    unverifiedRoleEnabled: bool = True
    unverifiedRoleName: str = "Unverified"  # deprecated
    unverifiedRole: str = None

    ageLimit: int = None
    disallowAlts: bool = None
    disallowBanEvaders: str = None  # Site sets it to "ban" when enabled. Null when disabled.
    groupLock: dict = None

    nicknameTemplate: str = DEFAULTS.get("nicknameTemplate")
    unverifiedNickname: str = None
    allowOldRoles: bool = False

    highTrafficServer: bool = None
    premium: dict = None

    # Old bind fields.
    roleBinds: dict = None
    groupIDs: dict = None
    converted_binds: bool = False
