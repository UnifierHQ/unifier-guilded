import guilded
from utils import platform_base

class WebhookCacheStore:
    def __init__(self, bot):
        self.bot = bot
        self.__webhooks = {}

    def store_webhook(self, webhook: guilded.Webhook):
        if not webhook.server.id in self.__webhooks.keys():
            self.__webhooks.update({webhook.server.id: {webhook.id: webhook}})
        self.__webhooks[webhook.server.id].update({webhook.id: webhook})
        return len(self.__webhooks[webhook.server.id])

    def store_webhooks(self, webhooks: list):
        for webhook in webhooks:
            if not webhook.guild.id in self.__webhooks.keys():
                self.__webhooks.update({webhook.server.id: {webhook.id: webhook}})
            self.__webhooks[webhook.server.id].update({webhook.id: webhook})
        return len(self.__webhooks)

    def get_webhooks(self, guild: int or str):
        try:
            guild = int(guild)
        except:
            pass
        if len(self.__webhooks[guild].values())==0:
            raise ValueError('no webhooks')
        return list(self.__webhooks[guild].values())

    def get_webhook(self, webhook: int or str):
        try:
            webhook = int(webhook)
        except:
            pass
        for guild in self.__webhooks.keys():
            if webhook in self.__webhooks[guild].keys():
                return self.__webhooks[guild][webhook]
        raise ValueError('invalid webhook')

    def clear(self, guild: int or str = None):
        if not guild:
            self.__webhooks = {}
        else:
            self.__webhooks[guild] = {}
        return

class GuildedPlatform(platform_base.PlatformBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_tb = True

    def get_server(self, server_id):
        return self.bot.get_server(server_id)

    def get_channel(self, channel_id):
        return self.bot.get_channel(channel_id)

    def channel(self, message: guilded.Message):
        return message.channel

    def server(self, message: guilded.Message):
        return message.server

    def content(self, message: guilded.Message):
        return message.content

    def member(self, message: guilded.Message):
        return message.author

    def attachments(self, message):
        return message.attachments

    def get_id(self, obj):
        return obj.id

    def display_name(self, user):
        return user.display_name or user.name

    def user_name(self, user):
        return user.name

    def avatar(self, user):
        return user.avatar.url.split('?')[0] if user.avatar else None

    def is_bot(self, user):
        return user.bot

    def attachment_size(self, attachment):
        return attachment.size

    def attachment_type(self, attachment):
        return attachment.content_type

    def convert_embeds(self, embeds):
        for i in range(len(embeds)):
            embed = guilded.Embed(
                title=embeds[i].title,
                description=embeds[i].description,
                url=embeds[i].url,
                colour=embeds[i].colour,
                timestamp=embeds[i].timestamp,
                icon_url=embeds[i].thumbnail.url
            )
            embed.set_footer(text=embeds[i].footer.text,icon_url=embeds[i].footer.icon_url)
            embeds[i] = embed
        return embeds
