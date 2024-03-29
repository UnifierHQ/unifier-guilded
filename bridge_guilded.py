"""
Unifier - A sophisticated Discord bot uniting servers and platforms
Copyright (C) 2024  Green, ItsAsheer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from discord.ext import commands
import guilded
from guilded.ext import commands as gd_commands
import asyncio
import traceback
import time
from time import strftime, gmtime
import json

whitelist = ['j7Deb6AR','jb7yGnPR']

with open('config.json', 'r') as file:
    data = json.load(file)

owner = data['owner']
external_services = data['external']
allow_prs = data["allow_prs"]
admin_ids = data['admin_ids']
pr_room_index = data["pr_room_index"] # If this is 0, then the oldest room will be used as the PR room.
pr_ref_room_index = data["pr_ref_room_index"]

class GuildedBot(gd_commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dc_bot = None

    def add_bot(self,bot):
        self.dc_bot: commands.Bot = bot


gd_bot = GuildedBot(command_prefix=data['prefix'])

def log(type='???',status='ok',content='None'):
    time1 = strftime("%Y.%m.%d %H:%M:%S", gmtime())
    if status=='ok':
        status = ' OK  '
    elif status=='error':
        status = 'ERROR'
    elif status=='warn':
        status = 'WARN '
    elif status=='info':
        status = 'INFO '
    else:
        raise ValueError('Invalid status type provided')
    print(f'[{type} | {time1} | {status}] {content}')

def is_user_admin(id):
    try:
        global admin_ids
        return id in admin_ids
    except:
        print("There was an error in 'is_user_admin(id)', for security reasons permission was resulted into denying!")
        return False

def is_room_restricted(room,db):
    try:
        return room in db['restricted']
    except:
        traceback.print_exc()
        return False

def is_room_locked(room,db):
    try:
        return room in db['locked']
    except:
        traceback.print_exc()
        return False

@gd_bot.event
async def on_ready():
    log('GLD','ok','Guilded client booted!')

@gd_bot.command(aliases=['hello'])
async def hi(ctx):
    return await ctx.send(f'Hi {ctx.author.name}! Guilded works!')

@gd_bot.command()
async def send(ctx,*,content):
    guild = gd_bot.dc_bot.get_guild(1196475780973207604)
    ch = guild.get_channel(1208761825898790965)
    await ch.send(content)
    await ctx.send('check discord')

@gd_bot.command(aliases=['link','connect','federate','bridge'])
async def bind(ctx,*,room=''):
    if not ctx.author.guild_permissions.manage_channels and not is_user_admin(ctx.author.id):
        return await ctx.send('You don\'t have the necessary permissions.')
    if is_room_restricted(room,gd_bot.dc_bot.db) and not is_user_admin(ctx.author.id):
        return await ctx.send('Only admins can bind channels to restricted rooms.')
    if room=='' or not room:
        room = 'main'
        await ctx.send('**No room was given, defaulting to main**')
    try:
        data = gd_bot.dc_bot.db['rooms_guilded'][room]
    except:
        return await ctx.send('This isn\'t a valid room. Try `main`, `pr`, `prcomments`, or `liveries` instead.')
    try:
        try:
            guild = data[f'{ctx.guild.id}']
        except:
            guild = []
        if len(guild) >= 1:
            return await ctx.send(f'Your server is already linked to this room.\n**Accidentally deleted the webhook?** `{gd_bot.dc_bot.command_prefix}unlink` it then `{gd_bot.dc_bot.command_prefix}link` it back.')
        index = 0
        text = ''
        if len(gd_bot.dc_bot.db['rules'][room])==0:
            text = f'No rules exist yet for this room! For now, follow the main room\'s rules.\nYou can always view rules if any get added using `{gd_bot.dc_bot.command_prefix}rules {room}`.'
        else:
            for rule in gd_bot.dc_bot.db['rules'][room]:
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
        newdata = gd_bot.dc_bot.db['rooms_guilded'][room]
        guild = [webhook.id]
        newdata.update({f'{ctx.guild.id}':guild})
        gd_bot.dc_bot.db['rooms_guilded'][room] = newdata
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
async def unbind(ctx,*,room=''):
    if room=='':
        return await ctx.send('You must specify the room to unbind from.')
    if not ctx.author.guild_permissions.manage_channels and not is_user_admin(ctx.author.id):
        return await ctx.send('You don\'t have the necessary permissions.')
    try:
        data = gd_bot.dc_bot.db['rooms_guilded'][room]
    except:
        return await ctx.send('This isn\'t a valid room. Try `main`, `pr`, `prcomments`, or `liveries` instead.')
    try:
        try:
            hooks = await ctx.guild.webhooks()
        except:
            return await ctx.send('I cannot manage webhooks.')
        if f'{ctx.guild.id}' in list(data.keys()):
            hook_ids = data[f'{ctx.guild.id}']
        else:
            hook_ids = []
        for webhook in hooks:
            if webhook.id in hook_ids:
                await webhook.delete()
                break
        data.pop(f'{ctx.guild.id}')
        gd_bot.dc_bot.db['rooms_guilded'][room] = data
        gd_bot.dc_bot.db.save_data()
        await ctx.send('Unlinked channel from network!')
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

@gd_bot.command(aliases=['ban'])
async def restrict(ctx, *, target):
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

@gd_bot.command(aliases=['unban'])
async def unrestrict(ctx, *, target):
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

    try:
        hooks = await message.channel.webhooks()
    except:
        hooks = await message.guild.webhooks()

    found = False
    origin_room = 0

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

    await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='guilded')
    await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='discord')
    for platform in external_services:
        if platform=='guilded':
            continue
        await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform=platform)

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
    # Autoleave from servers not in whitelist
    if not member.id=='m7QDO1a4':
        if not server.id in whitelist:
            log('GLD', 'info', f'Autoleave triggered: {server.name} ({server.id})')
            await server.leave()

class Guilded(commands.Cog,name='<:GuildedSupport:1220134640996843621> Guilded Support'):
    """An extension that enables Unifier to run on Guilded. Manages Guilded instance, as well as Guilded-to-Guilded and Guilded-to-external bridging.

    Developed by Green"""
    def __init__(self,bot):
        self.bot = bot
        if not 'guilded' in external_services:
            raise RuntimeError('guilded is not listed as an external service in config.json. More info: https://unichat-wiki.pixels.onl/setup-selfhosted/getting-started#installing-revolt-support')
        if not hasattr(self.bot, 'guilded_client'):
            self.bot.guilded_client = gd_bot
            self.bot.guilded_client_task = asyncio.create_task(self.guilded_boot())

    async def guilded_boot(self):
        if not self.bot.guilded_client.ws:
            log('DAT','info','Syncing Guilded rooms...')
            for key in self.bot.db['rooms']:
                if not key in list(self.bot.db['rooms_guilded'].keys()):
                    self.bot.db['rooms_guilded'].update({key: {}})
                    log('DAT','ok','Synced room '+key)
            self.bot.db.save_data()
            while True:
                try:
                    log('GLD', 'info', 'Booting Guilded client...')
                    self.bot.guilded_client.add_bot(self.bot)
                    await self.bot.guilded_client.start(data['guilded_token'])
                except:
                    log('GLD', 'error', 'Guilded client failed to boot!')
                    traceback.print_exc()
                    break
                log('GLD', 'warn', 'Guilded client has exited. Rebooting in 10 seconds...')
                try:
                    await asyncio.sleep(10)
                except:
                    log('GLD', 'error', 'Couldn\'t sleep, exiting loop...')
                    break

async def setup(bot):
    await bot.add_cog(Guilded(bot))