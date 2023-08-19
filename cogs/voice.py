import asyncio
import sqlite3
from textwrap import dedent
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
            guild_id = member.guild.id
            c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guild_id,))
            voice = c.fetchone()
            if voice is not None:
                voice_id = voice[0]
                try:
                    if after.channel.id == voice_id:
                        c.execute("SELECT * FROM voiceChannel WHERE userID = ?", (member.id,))
                        cooldown = c.fetchone()
                        if cooldown is not None:
                            await member.send(
                                "Creating channels too quickly you've been put on a 15 second cooldown!"
                            )
                            await asyncio.sleep(15)
                        c.execute("SELECT voiceCategoryID FROM guild WHERE guildID = ?", (guild_id,))
                        voice = c.fetchone()
                        c.execute(
                            "SELECT channelName, channelLimit FROM userSettings WHERE userID = ?",
                            (member.id,),
                        )
                        setting = c.fetchone()
                        c.execute(
                            "SELECT channelLimit FROM guildSettings WHERE guildID = ?", (guild_id,)
                        )
                        guild_setting = c.fetchone()
                        if setting is None:
                            name = f"{member.name}'s channel"
                            if guild_setting is None:
                                limit = 0
                            else:
                                limit = guild_setting[0]
                        else:
                            name = setting[0]
                            if guild_setting is None:
                                limit = setting[1]
                            elif guild_setting is not None and setting[1] == 0:
                                limit = guild_setting[0]
                            else:
                                limit = setting[1]
                        category_id = voice[0]
                        member_id = member.id
                        category = self.bot.get_channel(category_id)
                        channel_2 = await member.guild.create_voice_channel(name, category=category)
                        channel_id = channel_2.id
                        await member.move_to(channel_2)
                        await channel_2.set_permissions(
                            self.bot.user, connect=True, read_messages=True
                        )
                        await channel_2.set_permissions(member, connect=True, read_messages=True)
                        await channel_2.edit(name=name, user_limit=limit)
                        c.execute("INSERT INTO voiceChannel VALUES (?, ?)", (member_id, channel_id))
                        conn.commit()

                        def check_voice_member_count(a: discord.Member, b: discord.VoiceState, c: discord.VoiceState) -> bool:
                            return len(channel_2.members) == 0
                        await self.bot.wait_for("voice_state_update", check=check_voice_member_count)
                        await channel_2.delete()
                        await asyncio.sleep(3)
                        c.execute("DELETE FROM voiceChannel WHERE userID=?", (member_id,))
                except Exception as e:
                    print(f"OnVoiceUpdate: {e}")
            conn.commit()

    @staticmethod
    @commands.command()
    async def help(ctx: commands.Context) -> None:
        embed = discord.Embed(title="Help", description="", color=7506394)
        embed.set_author(
            name=f"{ctx.guild.me.display_name}",
            url="https://discordbots.org/bot/472911936951156740",
            icon_url=f"{ctx.guild.me.display_avatar.url}",
        )
        commands_text = dedent("""
            **Lock your channel by using the following command:**
            `.voice lock`
            ------------
            **Unlock your channel by using the following command:**
            `.voice unlock`
            ------------
            **Change your channel name by using the following command:**
            `.voice name <name>`
            **Example:** `.voice name EU 5kd+`
            ------------
            **Change your channel limit by using the following command:**
            `.voice limit number`
            **Example:** `.voice limit 2`
            ------------
            **Give users permission to join by using the following command:**
            `.voice permit @person`
            **Example:** `.voice permit @Sam#9452`
            ------------
            **Claim ownership of channel once the owner has left:**
            `.voice claim`
            **Example:** `.voice claim`
            ------------
            **Remove permission and the user from your channel using the following command:**
            `.voice reject @person`
            **Example:** `.voice reject @Sam#9452`
            """
        )
        embed.add_field(
            name="**Commands**",
            value=commands_text,
            inline="false",
        )
        embed.set_footer(text="Bot developed by Sam#9452")
        await ctx.channel.send(embed=embed)

    @staticmethod
    @commands.group()
    async def voice(ctx: commands.Context) -> None:
        pass

    @voice.command()
    async def setup(self, ctx: commands.Context) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            guild_id = ctx.guild.id
            author_id = ctx.author.id
            if ctx.author.id == ctx.guild.owner_id or ctx.author.id in self.bot.owner_ids:

                def check(m: commands.Context) -> bool:
                    # Check what?
                    return m.author.id == ctx.author.id
                await ctx.channel.send("**You have 60 seconds to answer each question!**")
                await ctx.channel.send("**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**")
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
                                "SELECT * FROM guild WHERE guildID = ? AND ownerID=?", (guild_id, author_id)
                            )
                            voice = c.fetchone()
                            if voice is None:
                                c.execute(
                                    "INSERT INTO guild VALUES (?, ?, ?, ?)",
                                    (guild_id, author_id, channel.id, new_cat.id),
                                )
                            else:
                                c.execute(
                                    "UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?",
                                    (guild_id, author_id, channel.id, new_cat.id, guild_id),
                                )
                            await ctx.channel.send("**You are all setup and ready to go!**")
                        except Exception:
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
    async def set_limit(ctx: commands.Context, number: int) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            if ctx.author.id == ctx.guild.owner.id or ctx.author.id == 151028268856770560:
                c.execute("SELECT * FROM guildSettings WHERE guildID = ?", (ctx.guild.id,))
                voice = c.fetchone()
                if voice is None:
                    c.execute(
                        "INSERT INTO guildSettings VALUES (?, ?, ?)",
                        (ctx.guild.id, f"{ctx.author.name}'s channel", number),
                    )
                else:
                    c.execute(
                        "UPDATE guildSettings SET channelLimit = ? WHERE guildID = ?",
                        (number, ctx.guild.id),
                    )
                await ctx.send("You have changed the default channel limit for your server!")
            else:
                await ctx.channel.send(
                    f"{ctx.author.mention} only the owner of the server can setup the bot!"
                )
            conn.commit()

    @staticmethod
    @setup.error
    async def info_error(ctx: commands.Context, error: Exception) -> None:
        print(error)

    @voice.command()
    async def lock(self, ctx: commands.Context) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (author_id,))
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
    async def unlock(self, ctx: commands.Context) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (author_id,))
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
    async def permit(self, ctx: commands.Context, member: discord.Member) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (author_id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                await channel.set_permissions(member, connect=True)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have permitted {member.name} to have access to the channel. ✅"
                )
            conn.commit()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx: commands.Context, member: discord.Member) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            guild_id = ctx.guild.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (author_id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                for members in channel.members:
                    if members.id == member.id:
                        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guild_id,))
                        voice = c.fetchone()
                        channel2 = self.bot.get_channel(voice[0])
                        await member.move_to(channel2)
                await channel.set_permissions(member, connect=False, read_messages=True)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌"
                )
            conn.commit()

    @voice.command()
    async def limit(self, ctx: commands.Context, limit: int) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (author_id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                await channel.edit(user_limit=limit)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have set the channel limit to be "
                    + "{}!".format(limit)
                )
                c.execute("SELECT channelName FROM userSettings WHERE userID = ?", (author_id,))
                voice = c.fetchone()
                if voice is None:
                    c.execute(
                        "INSERT INTO userSettings VALUES (?, ?, ?)",
                        (author_id, f"{ctx.author.name}", limit),
                    )
                else:
                    c.execute(
                        "UPDATE userSettings SET channelLimit = ? WHERE userID = ?", (limit, author_id)
                    )
            conn.commit()

    @voice.command()
    async def name(self, ctx: commands.Context, *, name: str) -> None:
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            author_id = ctx.author.id
            c.execute(SELECT_VOICE_ID_FROM_VOICE_CHANNEL_WHERE_USER_ID, (author_id,))
            voice = c.fetchone()
            if voice is None:
                await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
            else:
                channel_id = voice[0]
                channel = self.bot.get_channel(channel_id)
                await channel.edit(name=name)
                await ctx.channel.send(
                    f"{ctx.author.mention} You have changed the channel name to "
                    + "{}!".format(name)
                )
                c.execute("SELECT channelName FROM userSettings WHERE userID = ?", (author_id,))
                voice = c.fetchone()
                if voice is None:
                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?)", (author_id, name, 0))
                else:
                    c.execute(
                        "UPDATE userSettings SET channelName = ? WHERE userID = ?", (name, author_id)
                    )
            conn.commit()

    @staticmethod
    @voice.command()
    async def claim(ctx: commands.Context) -> None:
        x = False
        with sqlite3.connect(VOICE_DB) as conn:
            c = conn.cursor()
            channel = ctx.author.voice.channel
            if channel is None:
                await ctx.channel.send(f"{ctx.author.mention} you're not in a voice channel.")
            else:
                author_id = ctx.author.id
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
                            "UPDATE voiceChannel SET userID = ? WHERE voiceID = ?", (author_id, channel.id)
                        )
                conn.commit()
                conn.close()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(_Voice(bot))