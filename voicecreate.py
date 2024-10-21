import discord, traceback, sys, os, dotenv
from discord.ext import commands

# Load environment variables from .env file (if present)
dotenv.load_dotenv(dotenv_path="config.env")

# Ensure all required environment variables are set
if not os.getenv('DISCORD_TOKEN'):
    print('[error]: `DISCORD_TOKEN` environment variable required')
    sys.exit(1)

if not os.getenv('DISCORD_ADMIN'):
    print('[error]: `DISCORD_ADMIN` environment variable required')
    sys.exit(1)

intents = discord.Intents.default()
#Message content intent needs to be enabled in the developer portal for your chosen bot.
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

bot.remove_command("help")

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

bot.run(os.getenv('DISCORD_TOKEN'))
