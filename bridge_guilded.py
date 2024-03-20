import discord
from discord.ext import commands
import guilded
from guilded.ext import commands as gd_commands
import asyncio
import traceback
import aiohttp
from time import strftime, gmtime
import json


class GuildedBot(gd_commands.bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = None

    def add_bot(self,bot):
        """Adds a Discord bot to the Guilded client."""
        self.bot = bot

with open('config.json', 'r') as file:
    data = json.load(file)

owner = data['owner']
external_services = data['external']
allow_prs = data["allow_prs"]
admin_ids = data['admin_ids']
pr_room_index = data["pr_room_index"] # If this is 0, then the oldest room will be used as the PR room.
pr_ref_room_index = data["pr_ref_room_index"]

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

class Guilded(commands.Cog,name='<:revoltsupport:1211013978558304266> Guilded Support'):
    """An extension that enables Unifier to run on Guilded. Manages Guilded instance, as well as Guilded-to-Guilded and Guilded-to-external bridging.

    Developed by Green"""
    def __init__(self,bot):
        self.bot = bot
        if not 'revolt' in external_services:
            raise RuntimeError('guilded is not listed as an external service in config.json. More info: https://unichat-wiki.pixels.onl/setup-selfhosted/getting-started#installing-revolt-support')
        if not hasattr(self.bot, 'guilded_client'):
            self.bot.guilded_client = None
            self.guilded_client_task = asyncio.create_task(self.guilded_boot())

    async def guilded_boot(self):
        if self.bot.revolt_client is None:
            log('DAT','info','Syncing Guilded rooms...')
            for key in self.bot.db['rooms']:
                if not key in list(self.bot.db['rooms_guilded'].keys()):
                    self.bot.db['rooms_guilded'].update({key: {}})
                    log('DAT','ok','Synced room '+key)
            self.bot.db.save_data()
            gd_bot.add_bot(self.bot)
            while True:
                try:
                    self.bot.guilded_client = gd_bot
                    gd_bot.run(data['guilded_token'])
                except RuntimeError:
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