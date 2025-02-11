from typing import List
import yaml
import logging


class BotAccount:
    server: str
    email: str
    client_id: str
    client_secret: str
    access_token: str

    def __init__(self, server: str, email: str, client_id: str, client_secret: str, access_token: str) -> None:
        self.server = server
        self.email = email
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token

    def __repr__(self) -> str:
        return f"server: {self.server}, email: {self.email}"


class Instance:
    name: str
    limit: int

    def __init__(self, name: str, limit: int) -> None:
        self.name = name
        self.limit = limit if limit > 0 and limit <= 20 else 20

    def __repr__(self) -> str:
        return f"{self.name} (top {self.limit})"


class Config:
    bot_account: BotAccount
    interval: int = 60  # minutes
    log_level: str = "INFO"
    subscribed_instances: List = []
    filtered_instances: List = []
    profile: str = ""
    fields: dict = {}

    def __init__(self):
        # auth file containing login info
        auth = "/app/config/auth.yaml"
        # settings file containing subscriptions
        conf = "/app/config/config.yaml"

        # only load auth info
        with open(auth, "r") as configfile:
            config = yaml.load(configfile, Loader=yaml.Loader)
            logging.getLogger("Config").debug("Loading auth info")
            if (
                config
                and config.get("bot_account")
                and config["bot_account"].get("server")
                and config["bot_account"].get("email")
                and config["bot_account"].get("password")
            ):
                self.bot_account = BotAccount(
                    server=config["bot_account"]["server"],
                    email=config["bot_account"]["email"],
                    client_id=config["bot_account"]["client_id"],
                    client_secret=config["bot_account"]["client_secret"],
                    access_token=config["bot_account"]["access_token"],
                )
            else:
                logging.getLogger("Config").error(config)
                raise ConfigException("""Bot account config is incomplete or missing. Needs server, email, client_id, client_secret and access token.

                    To find out how to set up an application and access token see $YOURSERVER/settings/applications""")

        with open(conf, "r") as configfile:
            config = yaml.load(configfile, Loader=yaml.Loader)
            logging.getLogger("Config").debug("Loading settings")
            if config:
                self.interval = (
                    config["interval"] if config.get("interval") else self.interval
                )
                self.log_level = (
                    config["log_level"] if config.get("log_level") else self.log_level
                )

                self.profile = (
                    config["profile"] if config.get("profile") else self.profile
                )

                self.fields = (
                    {name: value for name, value in config["fields"].items()}
                    if config.get("fields")
                    else {}
                )

                self.subscribed_instances = (
                    [
                        Instance(name, props["limit"])
                        for name, props in config["subscribed_instances"].items()
                    ]
                    if config.get("subscribed_instances")
                    else []
                )

                self.filtered_instances = (
                    [name for name in config["filtered_instances"].items()]
                    if config.get("filtered_instances")
                    else []
                )


class ConfigException(Exception):
    pass
