import discord
import math
import asyncio
import aiohttp
import json
import datetime
from discord.ext import commands
import traceback
import sqlite3
from urllib.parse import quote
from discord.ext.commands.cooldowns import BucketType
from time import gmtime, strftime

import pdb


class voice(commands.Cog):
    ADMIN_BITMAP = 8
    PROMPT_TIMEOUT = 60

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def voice(self, ctx):
        pass

    @voice.command()
    async def setup(self, ctx):
        conn = sqlite3.connect('voice.db')
        c = conn.cursor()
        guildId = ctx.guild.id

        if self.isAdmin(ctx):

            if self.hasBeenSetup(c, guildId):
                await ctx.channel.send("**ERROR**: Public voice channels already set up")
                return

            await ctx.channel.send(f"Enter the name of the category you wish to create the channels in:")
            category = await self.setupPrompt(ctx)
            if category == None: return

            await ctx.channel.send("Enter the name of the voice channel:")
            channel = await self.setupPrompt(ctx)
            if channel == None: return

        category = await ctx.guild.create_category_channel(category.content)
        channel = await ctx.guild.create_voice_channel(channel.content, category=category)
                
        c.execute ("INSERT INTO guilds VALUES (?, ?, ?)",(guildId, category.id, channel.id))
        await ctx.channel.send("You are all setup and ready to go!")

        conn.commit()
        conn.close()
        return

    # https://discordapp.com/developers/docs/topics/permissions
    def isAdmin(self, ctx):
        callersPermissions = ctx.message.author.guild_permissions.value
    
        return callersPermissions & self.ADMIN_BITMAP == self.ADMIN_BITMAP

    async def setupPrompt(self, ctx):
        def check(m):
                return m.author.id == ctx.author.id
        response = None
        try:
            response = await self.bot.wait_for('message', check=check, timeout = self.PROMPT_TIMEOUT)
        except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!')

        return response
    
    def hasBeenSetup(self, cursor, guildId):
        cursor.execute("SELECT * FROM guilds WHERE guildId = ?", (guildId,))
        hasManagedChannels = cursor.fetchone()
        
        return hasManagedChannels != None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conn = sqlite3.connect('voice.db')
        c = conn.cursor()
        guildId = member.guild.id
        c.execute("SELECT * FROM guilds WHERE guildId = ?", (guildId,))
        guildInfo = c.fetchone()

        c.execute("SELECT channelId FROM channels WHERE guildId = ?", (guildId,))
        managedChannelsReturn = c.fetchall()
        managedChannels = [channelTuple[0] for channelTuple in managedChannelsReturn] 

        
        if self.requestedNewChannel(guildInfo, after):
            category = self.bot.get_channel(guildInfo[1])
            createdChannel = await member.guild.create_voice_channel("Public",category=category)
            await member.move_to(createdChannel)
            c.execute("INSERT INTO channels VALUES (?, ?)", (createdChannel.id,guildInfo[0]))
        
        if self.channelNeedsDeleted(before, after, managedChannels):
            await before.channel.delete()
            c.execute('DELETE FROM channels WHERE channelId=?', (before.channel.id,))

        conn.commit()
        conn.close()
    
    def requestedNewChannel(self, guildInfo, after):
        return guildInfo != None and after.channel != None and guildInfo[2] == after.channel.id

    def channelNeedsDeleted(self, before, after, managedChannels):
        return after.channel != before.channel and before.channel != None and len(before.channel.members) == 0 and before.channel.id in managedChannels

    @setup.error
    async def info_error(self, ctx, error):
        print(error)

def setup(bot):
    bot.add_cog(voice(bot))
