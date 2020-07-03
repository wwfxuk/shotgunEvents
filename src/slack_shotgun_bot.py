import collections
import os
import typing

# import shotgun_api3

from slack import WebClient

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_USER_TOKEN = os.environ["SLACK_USER_TOKEN"]
SLACK_BOT_APP_ID = os.environ["SLACK_BOT_APP_ID"]
SC_BOT = WebClient(token=SLACK_BOT_TOKEN)
SC_USER = WebClient(token=SLACK_USER_TOKEN)

SlackSgID = collections.namedtuple("SlackSgID", ["slack", "sg"])


class KnownUsers(collections.abc.MutableSet):
    def __init__(self):
        self._ids_set = set()

    def __contains__(self, *args, **kwargs):
        return self._ids_set.__contains__(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        return self._ids_set.__iter__(*args, **kwargs)

    def __len__(self, *args, **kwargs):
        return self._ids_set.__len__(*args, **kwargs)

    def refresh(self, shotgun):
        """Clear and re-assign all Slack and Shotgun ID mappings.

        Requires Slack app permissions (OAuth Scopes):
        - ``user.profile:read``
        - ``users:read``
        - ``users:read.email``
        """
        self.clear()
        query = [
            ["sg_status_list", "is", "act"],
            ["name", "is_not", "Template User"],
            ["name", "is_not", "Shotgun Support"],
        ]
        fields = ["email", "login", "name"]
        sg_people = shotgun.find("HumanUser", query, fields=fields)
        slack_people = {
            member["id"]: dict(member["profile"].items(), name=member["name"])
            for member in SC_BOT.users_list().data["members"]
            if not (member["is_bot"] or member["deleted"])
        }
        def get(mapping, key):
            return str(mapping.get(key) or "").lower()

        for slack_id, profile in slack_people.items():
            for sg_user in sg_people:
                sg_id = sg_user["id"]
                matched = (
                    get(sg_user, "email") == get(profile, "email")
                    or get(sg_user, "login") == get(profile, "name")
                    or get(sg_user, "name") in [
                        get(profile, "display_name"),
                        get(profile, "real_name"),
                    ]
                )
                if matched and self.slack_of(sg_id) is None:
                    self.add(slack_id, sg_id)
                    break


    def sg_of(self, slack_id: str, default=None) -> int:
        """Get Shotgun HumanUser ID for a given Slack ID."""
        finder = (sg_id for id_, sg_id in self._ids_set if id_ == slack_id)
        return next(finder, default)

    def slack_of(self, sg_id: int, default=None) -> str:
        """Get Slack ID for a given Shotgun HumanUser ID."""
        finder = (slack_id for slack_id, id_ in self._ids_set if id_ == sg_id)
        return next(finder, default)

    @typing.overload
    def discard(self, slack_id: str):
        """Add a given Slack and Shotgun ID separately."""

    @typing.overload
    def discard(self, sg_id: int):
        """Add a given Slack and Shotgun ID separately."""

    @typing.overload
    def discard(self, id_mapping: SlackSgID):
        """Add a Slack and Shotgun ID mapping."""

    def discard(self, id_):
        if isinstance(id_, int):
            id_mapping = SlackSgID(self.slack_of(id_), id_)
        elif isinstance(id_, str):
            id_mapping = SlackSgID(id_, self.sg_of(id_))
        elif isisntance(id_, SlackSgID):
            id_mapping = id_
        else:
            raise TypeError(f"Invalid ID to discard: {id_}")
        self._ids_set.discard(id_mapping)

    @typing.overload
    def add(self, slack_id: str, sg_id: int) -> SlackSgID:
        """Add a given Slack and Shotgun ID separately."""

    @typing.overload
    def add(self, id_mapping: SlackSgID) -> SlackSgID:
        """Add a Slack and Shotgun ID mapping."""

    def add(self, *args):
        args_count = len(args)
        if args_count == 2:
            id_mapping = SlackSgID(*args)
        elif args_count == 1:
            id_mapping = args[0]
        else:
            raise TypeError(
                f"Expected either 1 SlackSgID argument or 2 arguments: "
                f"Slack ID and Shotgun ID respectively. Got {args}"
            )

        if not isinstance(id_mapping, SlackSgID):
            type_ = type(id_mapping).__name__
            raise TypeError(f"id_mapping should be of type SlackSgID, not {type_}")
        self._ids_set.add(id_mapping)
        return id_mapping


KNOWN_USERS = KnownUsers()


def send_message(channel, message, attachments=None):
    """
    Sends a message as the the bot user.

    :param channel: A slack channel ID or user ID.
    :param message: The slack message.
    """
    slack_message = SC_BOT.api_call(
        "chat.postMessage",
        channel=channel,
        as_user=True,
        text=message,
        attachments=attachments,
    )
    return slack_message


def create_channel(channel_name, private=False):
    """
    Creates a new slack channel and returns the channel ID if successful.

    :param channel_name: the slack channel name.
    """
    channel_id = None
    if private:
        new_channel = SC_USER.api_call("groups.create", name=channel_name)
        if new_channel:
            channel_id = new_channel.get("group").get("id")
    else:
        new_channel = SC_USER.api_call("channels.create", name=channel_name)
        if new_channel:
            channel_id = new_channel.get("channel").get("id")
    if channel_id:
        invite_to_channel(SLACK_BOT_APP_ID, channel_id)
    return new_channel


def invite_to_channel(user, channel):
    """
    Invites a user to a channel.

    :param user: A slack user ID.
    :param channel: A slack channel ID.
    """
    if channel.startswith("G"):
        invite = SC_USER.api_call("groups.invite", user=user, channel=channel)
    else:
        invite = SC_USER.api_call("channels.invite", user=user, channel=channel)
    return invite


def kick_from_channel(user, channel):
    """
    Removes a user from a channel.

    :param user: A slack user ID.
    :param channel: A slack channel ID.
    """
    if channel.startswith("G"):
        kick = SC_USER.api_call("groups.kick", name=user, channel=channel)
    else:
        kick = SC_USER.api_call("channel.kick", name=user, channel=channel)
    return kick


def invite_to_workspace(email, channels=None):
    """
    Invites a new slack user to the workspace.

    :param email: The email adddress to end the invite.
    :param channel: A comma separated list of channel IDs for the new user.
    """
    # TODO: Test this. This is an undocumented slack method.
    invite = SC_USER.api_call("users.admin.invite", email=email, channels=channels)
    return invite


def get_slack_user_id(sg, shotgun_id, refresh=False):
    if refresh or not KNOWN_USERS:
        KNOWN_USERS.refresh(sg)
    return KNOWN_USERS.slack_of(shotgun_id)
