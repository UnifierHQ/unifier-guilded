import time

import discord
from discord.ext import commands
import guilded
from guilded.ext import commands as gd_commands
import asyncio
import traceback
import aiohttp
from time import strftime, gmtime
import json

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

@gd_bot.event
async def on_ready():
    log('RVT','ok','Guilded client booted!')

@gd_bot.command(aliases=['hello'])
async def hi(ctx):
    return await ctx.send(f'Hi {ctx.author.name}! Guilded works!')

@gd_bot.command()
async def send(ctx,*,content):
    guild = gd_bot.dc_bot.get_guild(1196475780973207604)
    ch = guild.get_channel(1208761825898790965)
    await ch.send(content)
    await ctx.send('check discord')

@gd_bot.event
async def on_message(message):
    roomname = None
    for key in gd_bot.dc_bot.db['rooms_revolt']:
        try:
            if message.channel.id in str(gd_bot.dc_bot.db['rooms_revolt'][key][message.server.id]):
                roomname = key
                break
        except:
            pass
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
    if message.content.startswith(gd_bot.command_prefix):
        return await gd_bot.process_commands(message)
    if not roomname:
        return
    thing = False
    if thing:
        await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='guilded')
        await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform='discord')
        for platform in external_services:
            if platform=='guilded':
                continue
            await gd_bot.dc_bot.bridge.send(room=roomname, message=message, platform=platform)

class Guilded(commands.Cog,name='<:revoltsupport:1211013978558304266> Guilded Support'):
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
                    self.bot.guilded_client.add_bot(self.bot)
                    await self.bot.guilded_client.start(data['guilded_token'])
                except:
                    log('RVT', 'error', 'Guilded client failed to boot!')
                    traceback.print_exc()
                    break
                log('RVT', 'warn', 'Guilded client has exited. Rebooting in 10 seconds...')
                try:
                    await asyncio.sleep(10)
                except:
                    log('RVT', 'error', 'Couldn\'t sleep, exiting loop...')
                    break

def setup(bot):
    bot.add_cog(Guilded(bot))