import asyncio
import sqlite3
import discord
from discord.ext import commands

VOICE_DB = "voice.db"
SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID = (
    "SELECT voiceID FROM voiceChannel WHERE userID = ?"
)

class _Voice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceChannel,
        after: discord.VoiceChannel
    ) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            guildID = member.guild.id
            c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
            voice = c.fetchone()
            if voice is not None:
                voiceID = voice[0]
                try:
                    if after.channel.id == voiceID:
                        c.execute("SELECT * FROM voiceChannel WHERE userID = ?", (member.id,))
                        cooldown = c.fetchone()
                        if cooldown is None:
                            pass
                        else:
                            await member.send(
                                "Creating channels too quickly you've been put on a 15 second cooldown!"
                            )
                            await asyncio.sleep(15)
                        c.execute("SELECT voiceCategoryID FROM guild WHERE guildID = ?", (guildID,))
                        voice = c.fetchone()
                        c.execute(
                            "SELECT channelName, channelLimit FROM userSettings WHERE userID = ?",
                            (member.id,),
                        )
                        setting = c.fetchone()
                        c.execute(
                            "SELECT channelLimit FROM guildSettings WHERE guildID = ?", (guildID,)
                        )
                        guildSetting = c.fetchone()
                        if setting is None:
                            name = f"{member.name}'s channel"
                            if guildSetting is None:
                                limit = 0
                            else:
                                limit = guildSetting[0]
                        else:
                            name = setting[0]
                            if guildSetting is None:
                                limit = setting[1]
                            elif guildSetting is not None and setting[1] == 0:
                                limit = guildSetting[0]
                            else:
                                limit = setting[1]
                        categoryID = voice[0]
                        id = member.id
                        category = self.bot.get_channel(categoryID)
                        channel2 = await member.guild.create_voice_channel(name, category=category)
                        channelID = channel2.id
                        await member.move_to(channel2)
                        await channel2.set_permissions(
                            self.bot.user, connect=True, read_messages=True
                        )
                        await channel2.set_permissions(member, connect=True, read_messages=True)
                        await channel2.edit(name=name, user_limit=limit)
                        c.execute("INSERT INTO voiceChannel VALUES (?, ?)", (id, channelID))
                        conn.commit()

                        def check(a, b, c):
                            return len(channel2.members) == 0
                        await self.bot.wait_for("voice_state_update", check=check)
                        await channel2.delete()
                        await asyncio.sleep(3)
                        c.execute("DELETE FROM voiceChannel WHERE userID=?", (id,))
                except:
                    pass
            conn.commit()

    @staticmethod
    @commands.command()
    async def help(ctx):
        embed = discord.Embed(title="Help", description="", color=7506394)
        embed.set_author(
            name=f"{ctx.guild.me.display_name}",
            url="https://discordbots.org/bot/472911936951156740",
            icon_url=f"{ctx.guild.me.display_avatar.url}",
        )
        embed.add_field(
            name=f"**Commands**",
            value=f"**Lock your channel by using the following command:**\n\n`.voice lock`\n\n------------\n\n**Unlock your channel by using the following command:**\n\n`.voice unlock`\n\n------------\n\n**Change your channel name by using the following command:**\n\n`.voice name <name>`\n\n**Example:** `.voice name EU 5kd+`\n\n------------\n\n**Change your channel limit by using the following command:**\n\n`.voice limit number`\n\n**Example:** `.voice limit 2`\n\n------------\n\n**Give users permission to join by using the following command:**\n\n`.voice permit @person`\n\n**Example:** `.voice permit @Sam#9452`\n\n------------\n\n**Claim ownership of channel once the owner has left:**\n\n`.voice claim`\n\n**Example:** `.voice claim`\n\n------------\n\n**Remove permission and the user from your channel using the following command:**\n\n`.voice reject @person`\n\n**Example:** `.voice reject @Sam#9452`\n\n",
            inline="false",
        )
        embed.set_footer(text="Bot developed by Sam#9452")
        await ctx.channel.send(embed=embed)

    @staticmethod
    @commands.group()
    async def voice(ctx):
        pass

    @voice.command()
    async def setup(self, ctx):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            guildID = ctx.guild.id
            id = ctx.author.id
            if ctx.author.id == ctx.guild.owner_id or ctx.author.id == 151028268856770560:

                def check(m):
                    return m.author.id == ctx.author.id
                await ctx.channel.send("**You have 60 seconds to answer each question!**")
                await ctx.channel.send(
                    f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**"
                )
                try:
                    category = await self.bot.wait_for("message", check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await ctx.channel.send("Took too long to answer!")
                else:
                    new_cat = await ctx.guild.create_category_channel(category.content)
                    await ctx.channel.send(
                        "**Enter the name of the voice channel: (e.g Join To Create)**"
                    )
                    try:
                        channel = await self.bot.wait_for("message", check=check, timeout=60.0)
                    except asyncio.TimeoutError:
                        await ctx.channel.send("Took too long to answer!")
                    else:
                        try:
                            channel = await ctx.guild.create_voice_channel(
                                channel.content, category=new_cat
                            )
                            c.execute(
                                "SELECT * FROM guild WHERE guildID = ? AND ownerID=?", (guildID, id)
                            )
                            voice = c.fetchone()
                            if voice is None:
                                c.execute(
                                    "INSERT INTO guild VALUES (?, ?, ?, ?)",
                                    (guildID, id, channel.id, new_cat.id),
                                )
                            else:
                                c.execute(
                                    "UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?",
                                    (guildID, id, channel.id, new_cat.id, guildID),
                                )
                            await ctx.channel.send("**You are all setup and ready to go!**")
                        except:
                            await ctx.channel.send(
                                "You didn't enter the names properly.\nUse `.voice setup` again!"
                            )
            else:
                await ctx.channel.send(
                    f"{ctx.author.mention} only the owner of the server can setup the bot!"
                )
            conn.commit()

    @staticmethod
    @commands.command()
    async def setlimit(ctx, num):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            if ctx.author.id == ctx.guild.owner.id or ctx.author.id == 151028268856770560:
                c.execute("SELECT * FROM guildSettings WHERE guildID = ?", (ctx.guild.id,))
                voice = c.fetchone()
                if voice is None:
                    c.execute(
                        "INSERT INTO guildSettings VALUES (?, ?, ?)",
                        (ctx.guild.id, f"{ctx.author.name}'s channel", num),
                    )
                else:
                    c.execute(
                        "UPDATE guildSettings SET channelLimit = ? WHERE guildID = ?",
                        (num, ctx.guild.id),
                    )
                await ctx.send("You have changed the default channel limit for your server!")
            else:
                await ctx.channel.send(
                    f"{ctx.author.mention} only the owner of the server can setup the bot!"
                )
            conn.commit()

    @staticmethod
    @setup.error
    async def info_error(ctx, error):
        print(error)

    @voice.command()
    async def lock(self, ctx):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channelID = voice[0]
                role = ctx.guild.default_role
                channel = self.bot.get_channel(channelID)
                await channel.set_permissions(role, connect=False)
                await ctx.channel.send(f"{ctx.author.mention} Voice chat locked! 🔒")
            conn.commit()

    @voice.command()
    async def unlock(self, ctx):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channelID = voice[0]
                role = ctx.guild.default_role
                channel = self.bot.get_channel(channelID)
                await channel.set_permissions(role, connect=True)
                await ctx.channel.send(f"{ctx.author.mention} Voice chat unlocked! 🔓")
            conn.commit()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, member: discord.Member):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channelID = voice[0]
                channel = self.bot.get_channel(channelID)
                await channel.set_permissions(member, connect=True)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have permited {member.name} to have access to the channel. ✅"
                )
            conn.commit()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, member: discord.Member):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            id = ctx.author.id
            guildID = ctx.guild.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channelID = voice[0]
                channel = self.bot.get_channel(channelID)
                for members in channel.members:
                    if members.id == member.id:
                        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
                        voice = c.fetchone()
                        channel2 = self.bot.get_channel(voice[0])
                        await member.move_to(channel2)
                await channel.set_permissions(member, connect=False, read_messages=True)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌"
                )
            conn.commit()

    @voice.command()
    async def limit(self, ctx, limit):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channelID = voice[0]
                channel = self.bot.get_channel(channelID)
                await channel.edit(user_limit=limit)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have set the channel limit to be "
                    + "{}!".format(limit)
                )
                c.execute("SELECT channelName FROM userSettings WHERE userID = ?", (id,))
                voice = c.fetchone()
                if voice is None:
                    c.execute(
                        "INSERT INTO userSettings VALUES (?, ?, ?)",
                        (id, f"{ctx.author.name}", limit),
                    )
                else:
                    c.execute(
                        "UPDATE userSettings SET channelLimit = ? WHERE userID = ?", (limit, id)
                    )
            conn.commit()

    @voice.command()
    async def name(self, ctx, *, name):
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channelID = voice[0]
                channel = self.bot.get_channel(channelID)
                await channel.edit(name=name)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have changed the channel name to "
                    + "{}!".format(name)
                )
                c.execute("SELECT channelName FROM userSettings WHERE userID = ?", (id,))
                voice = c.fetchone()
                if voice is None:
                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?)", (id, name, 0))
                else:
                    c.execute(
                        "UPDATE userSettings SET channelName = ? WHERE userID = ?", (name, id)
                    )
            conn.commit()

    @staticmethod
    @voice.command()
    async def claim(ctx):
        x = False
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            channel = ctx.author.voice.channel
            if channel is None:
                await ctx.channel.send(f"{ctx.author.mention} you're not in a voice channel.")
            else:
                id = ctx.author.id
                c.execute("SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel.id,))
                voice = c.fetchone()
                if voice is None:
                    await ctx.channel.send(f"{ctx.author.mention} You can't own that channel!")
                else:
                    for data in channel.members:
                        if data.id == voice[0]:
                            owner = ctx.guild.get_member(voice[0])
                            await ctx.channel.send(
                                f"{ctx.author.mention} This channel is already owned by {owner.mention}!"
                            )
                            x = True
                    if x is False:
                        await ctx.channel.send(
                            f"{ctx.author.mention} You are now the owner of the channel!"
                        )
                        c.execute(
                            "UPDATE voiceChannel SET userID = ? WHERE voiceID = ?", (id, channel.id)
                        )
                conn.commit()
                conn.close()


async def setup(bot):
    await bot.add_cog(_Voice(bot))