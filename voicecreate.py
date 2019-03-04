import discord
import math
import asyncio
import aiohttp
import json
from discord.ext import commands
from random import randint
import traceback
import sqlite3
import sys

client = discord.Client()

bot = commands.Bot(command_prefix=".")
bot.remove_command("help")
DISCORD_TOKEN = 'Enter Discord Token here'

initial_extensions = ['cogs.voice']

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.run(DISCORD_TOKEN)
