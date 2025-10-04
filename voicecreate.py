import discord
from discord.ext import commands
import traceback
import sys
import json


__config = dict()

try:
    with open("config.json", 'r', encoding="utf-8") as _f:
        __config = json.loads(_f.read())
        assert __config["token"]
except Exception as e:
    print("error reading config\n", e)
    exit(1)


intents = discord.Intents.default()
#Message content intent needs to be enabled in the developer portal for your chosen bot.
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

bot.remove_command("help")

DISCORD_TOKEN = 'Enter Discord Token here'

initial_extensions = ['cogs.voice']

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f'Loaded {extension}')
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()

bot.run(__config["token"])
