import discord
import os
import traceback
import sys
from discord.ext.commands import AutoShardedBot as asb

started = False

class VoiceMaster(asb):
    def __init__(self):
        super().__init__(
            command_prefix=".",
            case_insensitive=True,
            help_command=None,
            intents=discord.Intents.all() # remove this if you dont want to enable all intents
        )
        
        self.cog_blacklist = [
            "__init__.py",
            "functions.py"
        ]
        self.remove_command("help")
        self.token = "TOKEN HERE" # please consider using a secrets file or a token file with a .gitignore
        self.load_cogs()
    
    def load_cogs(self):
        if not started:
            print("Loading cogs:")
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and filename not in self.cog_blacklist:
                    try:
                        self.load_extension(f"cogs.{filename[:-3]}")
                        print(f"    Loaded '{filename}'")
                    except Exception as e:
                        print(str(e))
            started = not started

    async def on_connect(self):
        print("Connected")

    async def on_ready(self):
        print("Ready")

if __name__ == "__main__":
    bot = VoiceMaster()
    bot.run(bot.token)
