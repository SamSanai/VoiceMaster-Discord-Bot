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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conn = sqlite3.connect('voice.db')
        c = conn.cursor()
        guildID = member.guild.id
        pdb.set_trace()
        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
        voice=c.fetchone()
        if voice is None:
            pass
        else:
            voiceID = voice[0]
            try:
                if after.channel.id == voiceID:
                    c.execute("SELECT * FROM voiceChannel WHERE userID = ?", (member.id,))
                    cooldown=c.fetchone()
                    if cooldown is None:
                        pass
                    else:
                        await member.send("Creating channels too quickly you've been put on a 15 second cooldown!")
                        await asyncio.sleep(15)
                    c.execute("SELECT voiceCategoryID FROM guild WHERE guildID = ?", (guildID,))
                    voice=c.fetchone()
                    c.execute("SELECT channelName, channelLimit FROM userSettings WHERE userID = ?", (member.id,))
                    setting=c.fetchone()
                    c.execute("SELECT channelLimit FROM guildSettings WHERE guildID = ?", (guildID,))
                    guildSetting=c.fetchone()
                    if setting is None:
                        name = f"{member.name}'s channel"
                        if guildSetting is None:
                            limit = 0
                        else:
                            limit = guildSetting[0]
                    else:
                        if guildSetting is None:
                            name = setting[0]
                            limit = setting[1]
                        elif guildSetting is not None and setting[1] == 0:
                            name = setting[0]
                            limit = guildSetting[0]
                        else:
                            name = setting[0]
                            limit = setting[1]
                    categoryID = voice[0]
                    id = member.id
                    category = self.bot.get_channel(categoryID)
                    channel2 = await member.guild.create_voice_channel(name,category=category)
                    channelID = channel2.id
                    await member.move_to(channel2)
                    await channel2.set_permissions(self.bot.user, connect=True,read_messages=True)
                    await channel2.edit(name= name, user_limit = limit)
                    c.execute("INSERT INTO voiceChannel VALUES (?, ?)", (id,channelID))
                    conn.commit()
                    def check(a,b,c):
                        return len(channel2.members) == 0
                    await self.bot.wait_for('voice_state_update', check=check)
                    await channel2.delete()
                    await asyncio.sleep(3)
                    c.execute('DELETE FROM voiceChannel WHERE userID=?', (id,))
            except:
                pass
        conn.commit()
        conn.close()

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="Help", description="",color=0x7289da)
        embed.set_author(name="Voice Create",url="https://discordbots.org/bot/472911936951156740", icon_url="https://i.imgur.com/i7vvOo5.png")
        embed.add_field(name=f'**Commands**', value=f'**Lock your channel by using the following command:**\n\n`.voice lock`\n\n------------\n\n'
                        f'**Unlock your channel by using the following command:**\n\n`.voice unlock`\n\n------------\n\n'
                        f'**Change your channel name by using the following command:**\n\n`.voice name <name>`\n\n**Example:** `.voice name EU 5kd+`\n\n------------\n\n'
                        f'**Change your channel limit by using the following command:**\n\n`.voice limit number`\n\n**Example:** `.voice limit 2`\n\n------------\n\n'
                        f'**Give users permission to join by using the following command:**\n\n`.voice permit @person`\n\n**Example:** `.voice permit @Sam#9452`\n\n------------\n\n'
                        f'**Claim ownership of channel once the owner has left:**\n\n`.voice claim`\n\n**Example:** `.voice claim`\n\n------------\n\n'
                        f'**Remove permission and the user from your channel using the following command:**\n\n`.voice reject @person`\n\n**Example:** `.voice reject @Sam#9452`\n\n', inline='false')
        embed.set_footer(text='Bot developed by Sam#9452')
        await ctx.channel.send(embed=embed)

    @commands.group()
    async def voice(self, ctx):
        pass

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

    def cleanup(self):
        return 

    @voice.command()
    async def setup(self, ctx):
        conn = sqlite3.connect('voice.db')
        c = conn.cursor()
        guildID = ctx.guild.id
        id = ctx.author.id
        # pdb.set_trace()

        if self.isAdmin(ctx):
            await ctx.channel.send("**You have " +str(self.PROMPT_TIMEOUT) +" seconds to answer each question!**")

            await ctx.channel.send(f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**")
            category = await self.setupPrompt(ctx)
            if category == None: return

            await ctx.channel.send('**Enter the name of the voice channel: (e.g Join To Create)**')
            channel = await self.setupPrompt(ctx)
            if channel == None: return

        new_cat = await ctx.guild.create_category_channel(category.content)
        channel = await ctx.guild.create_voice_channel(channel.content, category=new_cat)

        # pdb.set_trace()
        return


        if ctx.author.id == ctx.guild.owner.id:
            def check(m):
                return m.author.id == ctx.author.id
            # await ctx.channel.send("**You have 60 seconds to answer each question!**")
            # await ctx.channel.send(f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**")
            try:
                category = await self.bot.wait_for('message', check=check, timeout = 60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!')
            else:
                new_cat = await ctx.guild.create_category_channel(category.content)
                await ctx.channel.send('**Enter the name of the voice channel: (e.g Join To Create)**')
                try:
                    channel = await self.bot.wait_for('message', check=check, timeout = 60.0)
                except asyncio.TimeoutError:
                    await ctx.channel.send('Took too long to answer!')
                else:
                    try:
                        channel = await ctx.guild.create_voice_channel(channel.content, category=new_cat)
                        c.execute("SELECT * FROM guild WHERE guildID = ? AND ownerID=?", (guildID, id))
                        voice=c.fetchone()
                        if voice is None:
                            c.execute ("INSERT INTO guild VALUES (?, ?, ?, ?)",(guildID,id,channel.id,new_cat.id))
                        else:
                            c.execute ("UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?",(guildID,id,channel.id,new_cat.id, guildID))
                        await ctx.channel.send("**You are all setup and ready to go!**")
                    except:
                        await ctx.channel.send("You didn't enter the names properly.\nUse `.voice setup` again!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner of the server can setup the bot!")
        conn.commit()
        conn.close()

    @setup.error
    async def info_error(self, ctx, error):
        print(error)

def setup(bot):
    bot.add_cog(voice(bot))
