import time
import schedule
import logging
from mastodon import Mastodon
from config import Config
import os.path


class Hype:
    def __init__(self, config: Config) -> None:
        self.config = config
        logging.basicConfig(
            format="%(asctime)s %(levelname)-8s %(message)s",
            level=logging.getLevelName(self.config.log_level),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.log = logging.getLogger("hype")
        self.log.info("Config loaded")

    def login(self):
        self.client = Mastodon(access_token=self.config.bot_account.access_token,
            api_base_url=self.config.bot_account.server,
            client_id=self.config.bot_account.client_id,
            client_secret=self.config.bot_account.client_secret,
            version_check_mode="none"
        )
        self.log.info(f"Logged in to {self.config.bot_account.server} (using OAUTH)")

    def update_profile(self):
        self.log.info("Update bot profile")
        note = self.config.profile
        fields = [(key, value) for key, value in self.config.fields.items()]
        self.client.account_update_credentials(
            note=note, bot=True, discoverable=True, fields=fields
        )

    def boost(self):
        self.log.info("Run boost")
        for instance in self.config.subscribed_instances:
            try:
                # Create mastodon API client
                mastodon_client = self.init_client(instance.name)
                # Fetch statuses from every subscribed instance
                trending_statuses = mastodon_client.trending_statuses()[
                    : instance.limit
                ]
                counter = 0
                for trending_status in trending_statuses:
                    counter += 1
                    # Get snowflake-id of status on the instance where the status will be boosted  # noqa: E501
                    status = self.client.search_v2(
                        trending_status["uri"], result_type="statuses"
                    )["statuses"]
                    if len(status) > 0:
                        status = status[0]
                        # check if post comes from a filtered instance
                        source_account = status["account"]["acct"].split("@")
                        server = source_account[1]
                        filtered = server in self.config.filtered_instances
                        # check if attached images have a description/alt text
                        images_described = True
                        for attachment in status.media_attachments:
                            if attachment.description is None or attachment.description=="":
                                images_described = False
                        # Boost if not already boosted
                        already_boosted = status["reblogged"]
                        if not already_boosted and not filtered and images_described:
                            self.client.status_reblog(status)
                            # if delay is set, wait for that amount of minutes
                            if self.config.delay:
                                self.log.info(f"Sleeping for {self.config.delay} seconds after boosting {status.url}")
                                time.sleep(self.config.delay)
                        self.log.info(
                            f"{instance.name}: {counter}/{len(trending_statuses)} {'ignore' if (already_boosted or filtered)  else 'boost'}"
                        )
                    else:
                        self.log.warning(
                            f"{instance.name}: {counter}/{len(trending_statuses)} could not find post by id"
                        )
            except Exception as e:
                self.log.error(
                    f"{instance.name}: Could not fetch instance. Sorry. - {e}"
                )

    def start(self):
        self.boost()
        self.log.info(f"Schedule run every {self.config.interval} minutes")
        schedule.every(self.config.interval).minutes.do(self.boost)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def init_client(self, instance_name: str) -> Mastodon:
        secret_path = f"secrets/{instance_name}_clientcred.secret"
        if not os.path.isfile(secret_path):
            self.log.info(f"Initialize client for {instance_name}")
            Mastodon.create_app(
                instance_name,
                api_base_url=f"https://{instance_name}",
                to_file=secret_path,
                scopes=['read']
            )
        else:
            self.log.info(f"Client for {instance_name} is already initialized.")

        return Mastodon(
                client_id=secret_path,
                ratelimit_method="pace",
            )
