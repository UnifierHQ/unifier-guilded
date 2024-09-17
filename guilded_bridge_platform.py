import nextcord
import guilded
from utils import platform_base

arrow_unicode = '\U0000250C'

class GuildedPlatform(platform_base.PlatformBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_tb = True
        self.uses_webhooks = True

    def bot_id(self):
        return self.bot.user.id

    # WebhookCacheStore wrapper for Guilded Support NUPS module
    def store_webhook(self, webhook: guilded.Webhook):
        return self.parent.bridge.webhook_cache.store_webhook(webhook, webhook.id, webhook.server.id)

    def store_webhooks(self, webhooks: list):
        return self.parent.bridge.webhook_cache.store_webhooks(
            webhooks, [webhook.id for webhook in webhooks], [webhooks[0].server.id] * len(webhooks)
        )

    def get_webhooks(self, guild: str):
        return self.parent.bridge.webhook_cache.get_webhooks(guild)

    def get_webhook(self, identifier: str):
        return self.parent.bridge.webhook_cache.get_webhook(identifier)

    def clear(self, guild: int or str = None):
        return self.parent.bridge.webhook_cache.clear(guild)

    # Guilded Support NUPS functions
    def get_server(self, server_id):
        return self.bot.get_server(server_id)

    def get_channel(self, channel_id):
        return self.bot.get_channel(channel_id)

    def get_user(self, user_id):
        return self.bot.get_user(user_id)

    def get_member(self, server, user_id):
        server = self.get_server(server)
        return server.get_member(user_id)

    def channel(self, message: guilded.ChatMessage):
        return message.channel

    def channel_id(self, obj):
        return obj.channel_id

    def server(self, message: guilded.ChatMessage):
        return message.server

    def server_id(self, obj):
        return obj.server_id

    def content(self, message: guilded.ChatMessage):
        return message.content

    def reply(self, message: guilded.ChatMessage or guilded.Message):
        if len(message.replied_to) == 0:
            return message.replied_to_ids[0]

        return message.replied_to[0]

    def roles(self, member: guilded.Member):
        pass

    def get_hex(self, role):
        # If the color is a gradient, use the first color value
        color = role.colors[0]
        return ''.join(f'{i:02X}' for i in (color.r, color.g, color.b))

    def author(self, message: guilded.ChatMessage):
        return message.author

    def embeds(self, message: guilded.ChatMessage):
        return message.embeds

    def attachments(self, message: guilded.ChatMessage):
        return message.attachments

    def url(self, message: guilded.ChatMessage):
        return message.share_url

    def get_id(self, obj):
        return obj.id

    def display_name(self, user: guilded.User):
        # Guilded doesn't have display names, so return username
        return user.name

    def user_name(self, user: guilded.User):
        return user.name

    def name(self, obj):
        return obj.name

    def avatar(self, user):
        return user.avatar.url.split('?')[0] if user.avatar else None

    def permissions(self, user: guilded.Member, channel=None):
        # we can't fetch permissions for a channel without using async, so use server permissions only
        user_perms = user.server_permissions

        permissions = platform_base.Permissions()
        permissions.ban_members = user_perms.ban_members
        permissions.manage_channels = user_perms.manage_channels
        return permissions

    def is_bot(self, user):
        return user.bot

    def attachment_size(self, attachment):
        if not attachment.size:
            # Guilded sometimes (or always?) doesn't provide the size of an attachment
            # If attachment.size is None, return 0
            return 0

        return attachment.size

    def attachment_type(self, attachment: guilded.Attachment):
        # We spent a great deal of time trying to figure this out for v2, thank guilded.py
        if not type(attachment.file_type) is guilded.FileType:
            # noinspection PyTypeChecker
            # ^ this stops pycharm from complaining because file_type should be namedtuple
            for value in list(attachment.file_type):
                if value == guilded.FileType.image:
                    return 'image'
                elif value == guilded.FileType.video:
                    return 'video'
                else:
                    return 'unknown'
        else:
            if attachment.file_type.image:
                return 'image'
            elif attachment.file_type.video:
                return 'video'
            else:
                return 'unknown'

    def convert_embeds(self, embeds: list):
        converted = []
        for i in range(len(embeds)):
            if not type(embeds[i]) is nextcord.Embed:
                continue
            embed = guilded.Embed(
                title=embeds[i].title,
                description=embeds[i].description,
                url=embeds[i].url,
                colour=embeds[i].colour.value,
                timestamp=embeds[i].timestamp or guilded.Embed.Empty,
            )
            embed.set_image(url=embeds[i].image.url or guilded.Embed.Empty)
            embed.set_thumbnail(url=embeds[i].thumbnail.url or guilded.Embed.Empty)
            embed.set_author(name=embeds[i].author.name, url=embeds[i].author.url, icon_url=embeds[i].author.icon_url)
            embed.set_footer(text=embeds[i].footer.text,icon_url=embeds[i].footer.icon_url)
            converted.append(embed)
        return converted

    def convert_embeds_discord(self, embeds: list):
        for i in range(len(embeds)):
            if not type(embeds[i]) is guilded.Embed:
                continue
            embed = nextcord.Embed(
                title=embeds[i].title,
                description=embeds[i].description,
                url=embeds[i].url,
                colour=embeds[i].colour.value,
                timestamp=embeds[i].timestamp,
            )
            embed.set_image(url=embeds[i].image.url)
            embed.set_thumbnail(url=embeds[i].thumbnail.url)
            embed.set_author(name=embeds[i].author.name, url=embeds[i].author.url, icon_url=embeds[i].author.icon_url)
            embed.set_footer(text=embeds[i].footer.text,icon_url=embeds[i].footer.icon_url)
            embeds[i] = embed
        return embeds

    def webhook_id(self, message):
        return message.webhook_id

    async def fetch_server(self, server_id):
        return await self.bot.fetch_server(server_id)

    async def fetch_channel(self, channel_id):
        return await self.bot.fetch_channel(channel_id)

    async def fetch_webhook(self, webhook_id, server_id):
        try:
            return self.get_webhook(webhook_id)
        except:
            server = await self.bot.getch_server(server_id)
            return await server.fetch_webhook(webhook_id)

    async def fetch_message(self, channel, message_id):
        return await channel.fetch_message(message_id)

    async def make_friendly(self, text: str):
        # Remove user mentions
        if len(text.split('<@')) > 1:
            for item in text.split('<@'):
                if not '>' in item:
                    # not a mention
                    continue

                user_id = list(item.split('>'))[0] # using list here to stop pycharm from complaining

                user = self.get_user(user_id)
                if not user:
                    continue

                text = text.replace(
                    f'<@{user_id}>', f'@{self.user_name(user)}'
                ).replace(
                    f'<@!{user_id}>', f'@{self.user_name(user)}'
                )

        # Remove channel mentions
        if len(text.split('<#')) > 1:
            for item in text.split('<#'):
                if not '>' in item:
                    # not a mention
                    continue

                channel_id = item.split('>')[0]

                channel = self.get_channel(channel_id)
                if not channel:
                    continue

                text = text.replace(
                    f'<#{channel_id}>', f'#{self.name(channel)}'
                ).replace(
                    f'<#!{channel_id}>', f'#{self.name(channel)}'
                )

        # Fix attachment URLs
        lines = text.split('\n')
        offset = 0
        for index in range(len(lines)):
            try:
                line = lines[index - offset]
            except:
                break
            if line.startswith('![](https://cdn.gilcdn.com/ContentMediaGenericFiles'):
                try:
                    lines.pop(index - offset)
                    offset += 1
                except:
                    pass
            elif line.startswith('![](') and line.endswith(')'):
                lines[index - offset] = line.replace('![](', '', 1)[:-1]

        if len(lines) == 0:
            text = ''
        else:
            text = '\n'.join(lines)

        return text

    async def to_discord_file(self, file: guilded.Attachment):
        tempfile = await file.to_file()
        # noinspection PyTypeChecker
        return nextcord.File(fp=tempfile.fp, filename=file.filename)

    async def to_platform_file(self, file: nextcord.Attachment):
        tempfile = await file.to_file(use_cached=True)
        return guilded.File(fp=tempfile.fp, filename=file.filename)

    async def send(self, channel, content, special: dict = None):
        files = special.get('files', [])
        embeds = special.get('embeds', [])
        reply = special.get('reply', None)
        reply_content = special.get('reply_content', None)

        if not files:
            files = []

        if not embeds:
            embeds = []

        if 'bridge' in special.keys():
            # check if we're in a room
            room = self.parent.bridge.get_channel_room(channel, platform='guilded')

            if room:
                webhook_id = self.parent.bridge.get_room(room)['guilded'][channel.server.id][0]
                try:
                    webhook = self.get_webhook(webhook_id)
                except:
                    server = self.get_server(channel.server.id)
                    webhook = await server.fetch_webhook(webhook_id)
                    self.store_webhook(webhook)
            else:
                raise ValueError('channel is not linked to a room, remove bridge from special')

            # as Guilded only supports ascii for usernames, remove all non-ascii characters
            # user emojis will be omitted
            name = special['bridge']['name'].encode("ascii", errors="ignore").decode()
            avatar = special['bridge']['avatar']

            replytext = ''

            if reply:
                # reply must be a UnifierMessage here
                # as reply cannot be none, PyUnresolvedReferences can be ignored
                reply_name = None

                try:
                    # noinspection PyUnresolvedReferences
                    if reply.source == 'discord':
                        # noinspection PyUnresolvedReferences
                        user = self.parent.get_user(int(reply.author))
                        reply_name = user.global_name or user.name
                    else:
                        # noinspection PyUnresolvedReferences
                        source_support = self.parent.bridge.platforms[reply.source]
                        # noinspection PyUnresolvedReferences
                        reply_name = source_support.display_name(source_support.get_user(reply.author))
                except:
                    pass

                if not reply_name:
                    reply_name = 'unknown'
                else:
                    reply_name = '@' + reply_name.replace('[','').replace(']','')

                # noinspection PyUnresolvedReferences
                if channel.server.id in reply.urls.keys():
                    # noinspection PyUnresolvedReferences
                    replytext = f'{arrow_unicode} **[Replying to {reply_name}]({reply.urls[channel.server.id]})**'
                else:
                    replytext = f'{arrow_unicode} **Replying to {reply_name}**'

                if reply_content:
                    replytext += f' - *{reply_content}*\n'
                else:
                    replytext += '\n'

            return await webhook.send(replytext + content, embeds=embeds, files=files, username=name, avatar_url=avatar)
        else:
            if reply:
                # reply must be an ID or ChatMessage here
                if type(reply) is str:
                    reply = await channel.fetch_message(reply)
                elif type(reply) is guilded.ChatMessage:
                    pass
                else:
                    reply = None
            return await channel.send(content, embeds=embeds, files=files, reply_to=[reply] if reply else None)

    async def edit(self, message: guilded.ChatMessage, content, special: dict = None):
        if message.webhook_id:
            # can't edit a webhook message
            return

        embeds = special.get('embeds', [])

        if not embeds:
            embeds = []

        await message.edit(content=content, embeds=embeds)

    async def delete(self, message):
        await message.delete()
