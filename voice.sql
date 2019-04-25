CREATE TABLE IF NOT EXISTS "guild" ( `guildID` INTEGER, `ownerID` INTEGER, `voiceChannelID` INTEGER, `voiceCategoryID` INTEGER );
GO;
CREATE TABLE IF NOT EXISTS  `guildSettings` ( `guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER );
GO;
CREATE TABLE IF NOT EXISTS `userSettings` ( `userID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER );
GO;
CREATE TABLE  IF NOT EXISTS `voiceChannel` ( `userID` INTEGER, `voiceID` INTEGER );
GO;
