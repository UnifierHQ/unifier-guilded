"""
Unifier - A sophisticated Discord bot uniting servers and platforms
Copyright (C) 2024  Green, ItsAsheer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from nextcord.ext import commands
import guilded
from guilded.ext import commands as gd_commands
import asyncio
import traceback
import time
from utils import log
import os

try:
    from utils import webhook_cache
except:
    # set this to none as this is a v2 installation
    webhook_cache = None

enable_whitelist = False
whitelist = []

class GuildedBot(gd_commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dc_bot = None
        self.logger = None
        self.compatibility_mode = False
        self.webhook_cache = None

    def add_bot(self,bot):
        self.dc_bot: commands.Bot = bot

    def add_logger(self,logger):
        self.logger = logger


gd_bot = GuildedBot(command_prefix='u!',features=guilded.ClientFeatures(official_markdown=True))
logger = None

admin_ids = []

def is_user_admin(user_id):
    try:
        return user_id in admin_ids
    except:
        return False

def is_room_restricted(room,db):
    try:
        return room in db['restricted']
    except:
        return False

def is_room_locked(room,db):
    try:
        return room in db['locked']
    except:
        return False

@gd_bot.event
async def on_ready():
    if not hasattr(gd_bot.dc_bot, 'platforms_former'):
        gd_bot.compatibility_mode = True
        return
    if 'guilded' in gd_bot.dc_bot.platforms.keys():
        gd_bot.dc_bot.platforms['guilded'].attach_bot(gd_bot)
    else:
        while not 'guilded' in gd_bot.dc_bot.platforms_former.keys():
            # wait until support plugin has been loaded
            await asyncio.sleep(1)
        gd_bot.dc_bot.platforms.update(
            {'guilded': gd_bot.dc_bot.platforms_former['guilded'].GuildedPlatform(gd_bot, gd_bot.dc_bot)}
        )
    await gd_bot.dc_bot.bridge.optimize(platform='guilded')
    if webhook_cache and not gd_bot.compatibility_mode:
        # noinspection PyUnresolvedReferences
        gd_bot.webhook_cache = webhook_cache.WebhookCacheStore(gd_bot)
    gd_bot.logger.info('Guilded client booted!')

@gd_bot.command(aliases=['link','connect','federate','bridge'])
async def bind(ctx,*,room):
    if not ctx.author.guild_permissions.manage_channels and not is_user_admin(ctx.author.id):
        return await ctx.send('You don\'t have the necessary permissions.')
    if is_room_restricted(room,gd_bot.dc_bot.db) and not is_user_admin(ctx.author.id):
        return await ctx.send('Only admins can bind channels to restricted rooms.')
    try:
        data = gd_bot.dc_bot.db['rooms'][room]
    except:
        return await ctx.send(f'This isn\'t a valid room. Run `{gd_bot.command_prefix}rooms` for a list of rooms.')
    if gd_bot.compatibility_mode:
        roomkey = 'rooms_guilded'
        if not room in gd_bot.dc_bot.db['rooms_guilded'].keys():
            return await ctx.send(
                f'You need to run `{gd_bot.dc_bot.command_prefix}restart-guilded` on Discord for this room to be available.'
            )
    else:
        roomkey = 'rooms'
        if data['meta']['private']:
            return await ctx.send('Private Rooms are not supported yet!')

    duplicate = None
    if gd_bot.compatibility_mode:
        for roomname in list(gd_bot.dc_bot.db[roomkey].keys()):
            # Prevent duplicate binding
            try:
                channel = gd_bot.dc_bot.db[roomkey][roomname][f'{ctx.guild.id}'][0]
                if channel == ctx.channel.id:
                    duplicate = roomname
                    break
            except:
                continue
    else:
        duplicate = gd_bot.dc_bot.bridge.check_duplicate(ctx.channel, platform='guilded')

    if duplicate:
        return await ctx.send(
            f'This channel is already linked to `{duplicate}`!\nRun `{gd_bot.command_prefix}unbind {duplicate}` to unbind from it.'
        )

    try:
        try:
            guild = data[f'{ctx.guild.id}']
        except:
            guild = []
        if len(guild) >= 1:
            return await ctx.send(f'Your server is already linked to this room.\n**Accidentally deleted the webhook?** `{gd_bot.dc_bot.command_prefix}unlink` it then `{gd_bot.dc_bot.command_prefix}link` it back.')
        index = 0
        text = ''
        if gd_bot.compatibility_mode:
            rules = gd_bot.dc_bot.db['rules'][room]
        else:
            rules = gd_bot.dc_bot.bridge.get_room(room)['meta']['rules']
        if len(rules)==0:
            text = f'No rules exist yet for this room! For now, follow the main room\'s rules.\nYou can always view rules if any get added using `{gd_bot.dc_bot.command_prefix}rules {room}`.'
        else:
            for rule in rules:
                if text=='':
                    text = f'1. {rule}'
                else:
                    text = f'{text}\n{index}. {rule}'
                index += 1
        text = f'{text}\n\nPlease display these rules somewhere accessible.'
        embed = guilded.Embed(title='Please agree to the room rules first:',description=text)
        embed.set_footer(text='Failure to follow room rules may result in user or server restrictions.')
        msg = await ctx.send(f'Please send "{gd_bot.dc_bot.command_prefix}agree" to bind to the room.',embed=embed)

        def check(message):
            return message.author.id==ctx.author.id

        try:
            resp = await gd_bot.wait_for("message",timeout=60,check=check)
        except:
            return await ctx.send('Timed out.')

        if not resp.content==f'{gd_bot.dc_bot.command_prefix}agree':
            return
        webhook = await ctx.channel.create_webhook(name='Unifier Bridge')
        if gd_bot.compatibility_mode:
            gd_bot.dc_bot.db['rooms_guilded'][room].update({f'{ctx.guild.id}':[webhook.id, ctx.channel.id]})
        else:
            await gd_bot.dc_bot.bridge.join_room(ctx.author, room, ctx.channel, platform='guilded', webhook_id=webhook.id)
        gd_bot.dc_bot.db.save_data()
        await ctx.send('Linked channel with network!')

        try:
            await msg.pin()
        except:
            pass
    except:
        await ctx.send('Something went wrong - check my permissions.')
        raise

@gd_bot.command(aliases=['unlink','disconnect'])
async def unbind(ctx,*,room=None):
    if not room:
        # room autodetect
        if not gd_bot.compatibility_mode:
            room = gd_bot.dc_bot.bridge.check_duplicate(ctx.channel, platform='revolt')
        if not room:
            return await ctx.send('This channel is not connected to a room.')
    if not ctx.author.guild_permissions.manage_channels and not is_user_admin(ctx.author.id):
        return await ctx.send('You don\'t have the necessary permissions.')
    if gd_bot.compatibility_mode:
        rooms = list(gd_bot.dc_bot.db['rooms_guilded'].keys())
    else:
        rooms = gd_bot.dc_bot.bridge.rooms
    if not room in rooms:
        return await ctx.send('This isn\'t a valid room.')
    try:
        if gd_bot.compatibility_mode:
            data = gd_bot.dc_bot.db['rooms_guilded'][room]
        else:
            data = gd_bot.dc_bot.bridge.get_room(room.lower())['guilded']

        hook_deleted = True
        try:
            hooks = await ctx.server.webhooks()
            if f'{ctx.server.id}' in list(data.keys()):
                hook_ids = data[f'{ctx.server.id}']
            else:
                hook_ids = []
            for webhook in hooks:
                if webhook.id in hook_ids:
                    await webhook.delete()
                    break
        except:
            hook_deleted = False

        if gd_bot.compatibility_mode:
            gd_bot.dc_bot.db['rooms_guilded'][room].pop(f'{ctx.server.id}')
            gd_bot.dc_bot.db.save_data()
        else:
            await gd_bot.dc_bot.bridge.leave_room(ctx.server, room, platform='guilded')

        if hook_deleted:
            await ctx.send('Unlinked channel from network!')
        else:
            await ctx.send('Unlinked channel from network, but webhook cold not be deleted')
    except:
        await ctx.send('Something went wrong - check my permissions.')
        raise

@gd_bot.command()
async def delete(ctx, *, msg_id=None):
    """Deletes all bridged messages. Does not delete the original."""
    gbans = gd_bot.dc_bot.db['banned']
    ct = time.time()
    if f'{ctx.author.id}' in list(gbans.keys()):
        banuntil = gbans[f'{ctx.author.id}']
        if ct >= banuntil and not banuntil == 0:
            gd_bot.dc_bot.db['banned'].pop(f'{ctx.author.id}')
            gd_bot.dc_bot.db.update()
        else:
            return
    if f'{ctx.guild.id}' in list(gbans.keys()):
        banuntil = gbans[f'{ctx.guild.id}']
        if ct >= banuntil and not banuntil == 0:
            gd_bot.dc_bot.db['banned'].pop(f'{ctx.guild.id}')
            gd_bot.dc_bot.db.update()
        else:
            return
    if f'{ctx.author.id}' in list(gbans.keys()) or f'{ctx.guild.id}' in list(gbans.keys()):
        return await ctx.send('Your account or your guild is currently **global restricted**.')

    try:
        msg_id = ctx.message.replied_to[0].id
    except:
        if not msg_id:
            return await ctx.send('No message!')

    try:
        msg = await gd_bot.dc_bot.bridge.fetch_message(msg_id)
    except:
        return await ctx.send('Could not find message in cache!')

    if not ctx.author.id==msg.author_id and not ctx.author.id in gd_bot.dc_bot.moderators:
        return await ctx.send('You didn\'t send this message!')

    try:
        await gd_bot.dc_bot.bridge.delete_parent(msg_id)
        if msg.webhook:
            raise ValueError()
        return await ctx.send('Deleted message (parent deleted, copies will follow)')
    except:
        try:
            deleted = await gd_bot.dc_bot.bridge.delete_copies(msg_id)
            return await ctx.send(f'Deleted message ({deleted} copies deleted)')
        except:
            traceback.print_exc()
            await ctx.send('Something went wrong.')

@gd_bot.command()
async def block(ctx, *, target):
    if not ctx.author.get_permissions().kick_members and not ctx.author.get_permissions().ban_members:
        return await ctx.send('You cannot restrict members/servers.')
    try:
        userid = int(target.replace('<@', '', 1).replace('!', '', 1).replace('>', '', 1))
        if userid == ctx.author.id:
            return await ctx.send('You can\'t restrict yourself :thinking:')
        if userid == ctx.guild.id:
            return await ctx.send('You can\'t restrict your own server :thinking:')
    except:
        userid = target
        if not len(userid) == 26:
            return await ctx.send('Invalid user/server!')
    if userid in gd_bot.dc_bot.moderators:
        return await ctx.send(
            'UniChat moderators are immune to blocks!\n(Though, do feel free to report anyone who abuses this immunity.)')
    banlist = []
    if f'{ctx.guild.id}' in list(gd_bot.dc_bot.db['blocked'].keys()):
        banlist = gd_bot.dc_bot.db['blocked'][f'{ctx.guild.id}']
    else:
        gd_bot.dc_bot.db['blocked'].update({f'{ctx.guild.id}': []})
    if userid in banlist:
        return await ctx.send('User/server already banned!')
    gd_bot.dc_bot.db['blocked'][f'{ctx.guild.id}'].append(userid)
    gd_bot.dc_bot.db.save_data()
    await ctx.send('User/server can no longer forward messages to this channel!')

@gd_bot.command()
async def unblock(ctx, *, target):
    if not ctx.author.get_permissions().kick_members and not ctx.author.get_permissions().ban_members:
        return await ctx.send('You cannot unrestrict members/servers.')
    try:
        userid = int(target.replace('<@', '', 1).replace('!', '', 1).replace('>', '', 1))
    except:
        userid = target
        if not len(target) == 26:
            return await ctx.send('Invalid user/server!')
    banlist = []
    if f'{ctx.guild.id}' in list(gd_bot.dc_bot.db['blocked'].keys()):
        banlist = gd_bot.dc_bot.db['blocked'][f'{ctx.guild.id}']
    if not userid in banlist:
        return await ctx.send('User/server not banned!')
    gd_bot.dc_bot.db['blocked'][f'{ctx.guild.id}'].remove(userid)
    gd_bot.dc_bot.db.save_data()
    await ctx.send('User/server can now forward messages to this channel!')

@gd_bot.event
async def on_message(message):
    if message.author.id == gd_bot.user.id:
        return
    if message.webhook_id:
        return

    t = time.time()
    if message.author.id in f'{gd_bot.dc_bot.db["banned"]}':
        if t >= gd_bot.dc_bot.db["banned"][message.author.id]:
            gd_bot.dc_bot.db["banned"].pop(message.author.id)
            gd_bot.dc_bot.db.save_data()
        else:
            return
    if message.server.id in f'{gd_bot.dc_bot.db["banned"]}':
        if t >= gd_bot.dc_bot.db["banned"][message.server.id]:
            gd_bot.dc_bot.db["banned"].pop(message.server.id)
            gd_bot.dc_bot.db.save_data()
        else:
            return
    if message.content.startswith(gd_bot.command_prefix):
        return await gd_bot.process_commands(message)

    if gd_bot.compatibility_mode:
        found = False
        origin_room = 0

        hooks = await message.channel.webhooks()
        for webhook in hooks:
            index = 0
            for key in gd_bot.dc_bot.db['rooms_guilded']:
                data = gd_bot.dc_bot.db['rooms_guilded'][key]
                if f'{message.server.id}' in list(data.keys()):
                    hook_ids = data[f'{message.server.id}']
                else:
                    hook_ids = []
                if webhook.id in hook_ids:
                    origin_room = index
                    found = True
                    break
                index += 1
            if found:
                break

        if not found:
            return

        roomname = list(gd_bot.dc_bot.db['rooms_guilded'].keys())[origin_room]
    else:
        roomname = gd_bot.dc_bot.bridge.get_channel_room(message.channel, platform='guilded')

        if not roomname:
            return

    if gd_bot.compatibility_mode:
        await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='guilded')
        await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='discord')
    else:
        await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='guilded', source='guilded')
        await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='discord', source='guilded')
    for platform in gd_bot.dc_bot.config['external']:
        if platform=='guilded':
            continue
        if gd_bot.compatibility_mode:
            await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform=platform)
        else:
            await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform=platform, source='guilded')

@gd_bot.event
async def on_message_delete(message):
    if message.webhook_id:
        return
    if message.author.id == gd_bot.user.id:
        return
    t = time.time()
    if message.author.id in f'{gd_bot.dc_bot.db["banned"]}':
        if t >= gd_bot.dc_bot.db["banned"][message.author.id]:
            gd_bot.dc_bot.db["banned"].pop(message.author.id)
            gd_bot.dc_bot.db.save_data()
        else:
            return
    if message.server.id in f'{gd_bot.dc_bot.db["banned"]}':
        if t >= gd_bot.dc_bot.db["banned"][message.server.id]:
            gd_bot.dc_bot.db["banned"].pop(message.server.id)
            gd_bot.dc_bot.db.save_data()
        else:
            return
    try:
        msgdata = await gd_bot.dc_bot.bridge.fetch_message(message.id)
        if not msgdata.id == message.id:
            raise ValueError()
    except:
        return

    await gd_bot.dc_bot.bridge.delete_copies(msgdata.id)

@gd_bot.event
async def on_bot_add(server, member):
    # Autoleave from servers not in whitelist, unless the owner added the bot to the server
    if not member.id == gd_bot.dc_bot.config['owner_external']['guilded'] and enable_whitelist:
        if not server.id in whitelist:
            gd_bot.logger.info(f'Autoleave triggered: {server.name} ({server.id})')
            await server.leave()

class Guilded(commands.Cog,name='<:GuildedSupport:1220134640996843621> Guilded Support'):
    """An extension that enables Unifier to run on Guilded. Manages Guilded instance, as well as Guilded-to-Guilded and Guilded-to-external bridging.

    Developed by Green"""
    def __init__(self,bot):
        global enable_whitelist
        global whitelist
        global admin_ids

        self.bot = bot
        if not 'guilded' in self.bot.config['external']:
            raise RuntimeError('guilded is not listed as an external service in config.json. More info: https://unichat-wiki.pixels.onl/setup-selfhosted/getting-started#installing-revolt-support')
        if not hasattr(self.bot, 'guilded_client'):
            self.bot.guilded_client = gd_bot
            self.bot.guilded_client.command_prefix = self.bot.command_prefix
            self.bot.guilded_client_task = asyncio.create_task(self.guilded_boot())
        self.logger = log.buildlogger(self.bot.package, 'guilded.core', self.bot.loglevel)

        if hasattr(self.bot, 'plugin_config'):
            if 'guilded' in self.bot.plugin_config.keys():
                plugin_config = self.bot.plugin_config['guilded']

                if 'whitelist' in plugin_config.keys():
                    enable_whitelist = plugin_config['whitelist'].get('enable_whitelist', False)
                    whitelist = plugin_config['whitelist'].get('whitelist', [])

        admin_ids = self.bot.admins

    async def guilded_boot(self):
        if not self.bot.guilded_client.ws:
            if not hasattr(self.bot, 'platforms_former'):
                self.logger.warning('Guilded Support is starting in legacy mode (non-NUPS).')
                self.logger.info('Syncing Guilded rooms...')
                for key in self.bot.db['rooms']:
                    if not key in list(self.bot.db['rooms_guilded'].keys()):
                        self.bot.db['rooms_guilded'].update({key: {}})
                        self.logger.debug('Synced room '+key)
                self.bot.db.save_data()
            while True:
                try:
                    self.logger.info('Booting Guilded client...')
                    self.bot.guilded_client.add_bot(self.bot)
                    self.bot.guilded_client.add_logger(log.buildlogger(self.bot.package, 'guilded.client', self.bot.loglevel))
                    if hasattr(self.bot, 'tokenstore'):
                        await self.bot.guilded_client.start(self.bot.tokenstore.retrieve('TOKEN_GUILDED'))
                    else:
                        await self.bot.guilded_client.start(os.environ.get('TOKEN_GUILDED'))
                except:
                    self.logger.exception('Guilded client failed to boot!')
                    break
                self.logger.warn('Guilded client has exited. Rebooting in 10 seconds...')
                try:
                    await asyncio.sleep(10)
                except:
                    self.logger.error('Couldn\'t sleep, exiting loop...')
                    break

    @commands.command(name='stop-guilded', hidden=True)
    async def stop_guilded(self, ctx):
        """Stops the Guilded client. This is automatically done when upgrading Unifier."""
        if not ctx.author.id == self.bot.config['owner']:
            return
        try:
            await self.bot.guilded_client.close()
            self.bot.guilded_client_task.cancel()
            del self.bot.guilded_client
            self.bot.unload_extension('cogs.bridge_guilded')
            await ctx.send(f'Guilded client stopped.\nTo restart, run `{self.bot.command_prefix}load guilded`')
        except Exception as e:
            if isinstance(e, AttributeError):
                return await ctx.send('Guilded client is already offline.')
            traceback.print_exc()
            await ctx.send('Something went wrong while stopping the instance.')

    @commands.command(name='restart-guilded', hidden=True)
    async def restart_guilded(self, ctx):
        """Restarts the Guilded client."""
        if not ctx.author.id == self.bot.config['owner']:
            return
        try:
            await self.bot.guilded_client.close()
            self.bot.guilded_client_task.cancel()
            del self.bot.guilded_client
            self.bot.reload_extension('cogs.bridge_guilded')
            await ctx.send('Guilded client restarted.')
        except Exception as e:
            if isinstance(e, AttributeError):
                return await ctx.send('Guilded client is not offline.')
            traceback.print_exc()
            await ctx.send('Something went wrong while restarting the instance.')

def setup(bot):
    bot.add_cog(Guilded(bot))
