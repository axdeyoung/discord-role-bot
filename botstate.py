
import discord
import pickle

### GuildData class manages data for a single server
# needs to be picklable
class BotState:
    """docstring for BotState"""

    # members:
        # roleDict: Dictionary of (discord.Guild.id : (discord.role.name : discord.role.id))
        # channelDict: a Dictionary of (discord.Guild.id : discord.TextChannel.id); home channel in each guild
        # saveFileName: str; 

    def __init__(self, saveFileName:str):
        self.roleDict = dict()
        self.channelDict = dict()
        self.saveFileName = saveFileName
        try:
            with open(saveFileName, "rb") as file:
                loaded = pickle.load(file)
                self.roleDict = loaded.roleDict
                self.channelDict = loaded.channelDict
            print("Loaded bot state from {0}".format(saveFileName))
        except:
            print("Created new bot state to be saved as {0}".format(saveFileName))

    def save(self):
        with open(self.saveFileName, "wb") as file:
            pickle.dump(self, file)


    async def addRole(self, roleName:str, guild:discord.Guild):
        '''
        Creates a role on the specified guild if one with the given name doesn't already exist
        Returns: True if the role was created successfully
        Returns: False if a role with that name is already managed by the bot
        '''
        #if discord.utils.get(guild.roles, name=roleName) == None:
        if roleName not in self.roleDict:
            role = await guild.create_role(name=roleName, colour=0x000033, mentionable=True)
            if guild.id not in self.roleDict:
                self.roleDict[guild.id] = dict()
            self.roleDict[guild.id][role.name] = role.id
            self.save()
            return True
        else:
            return False

    async def deleteRole(self, roleName:str, guild:discord.Guild):
        '''
        Returns True if role successfully deleted
        Returns False if role is not managed
        '''
        # the order of the following two remove/delete are important
        # if the role was deleted on Discord, it will automatically
        # sync the bot state with the Discord state
        try:
            # first try to remove the role from the bot state
            roleID = self.roleDict[guild.id].pop(roleName)
            if not self.roleDict[guild.id]: #if the dictionary for this guild is empty
                self.roleDict.pop(guild.id)
            self.save()
            

            # if the role was successfully removed from the bot state, try to delete the role from Discord
            role = guild.get_role(roleID)
            await role.delete()
        except:
            return False
        return True
    
    def getManagedRoles(self, guild:discord.Guild):
        '''
        Returns a List of roles managed by the bot in the given guild.
        Returns an empty list if the bot does not manage any roles in the given guild.
        '''
        # check if the given guild has any managed roles
        if guild.id in self.roleDict:
            # convert the managed role names to role objects and return them.
            return [self.getRoleFromName(role_name, guild) for role_name in self.roleDict[guild.id]]
        else:
            # return an empty list if the given guild doesn't manage any roles.
            return []

    def getRoleFromName(self, roleName:str, guild:discord.Guild):
        roleID = None
        role = None
        try:
            roleID = self.roleDict[guild.id][roleName]
        except:
            return None

        try:
            role = guild.get_role(roleID)
        except:
            # if the role exists in the bot state but not on the server
            # delete the role from the bot state
            self.deleteRole(roleName, guild)
            return None
        return role

    def getRoleNamesFromMember(self, member:discord.Member):
        '''
        Returns: List[str], the list of role names assigned to the member
        '''
        # print("Running getRoleNamesFromMember({0} : {1})".format(member.name, member.id))
        # if this guild doesn't have any bot-managed roles, return an empty list
        guild = member.guild
        if guild.id not in self.roleDict:
            print("Member's guild not registered.")
            return list()

        roleNames = list()

        guildRoles = self.roleDict[guild.id]

        for memberRole in member.roles:
            # print("\tChecking role {}".format(memberRole.name))
            if memberRole.name in guildRoles:
                # print("\t\tMatch found!")
                roleNames.append(memberRole.name)
        
        return roleNames

    def getMembersInRoleName(self, roleName:str, guild:discord.Guild):
        '''
        Returns: List[discord.Member]
        Returns: None, if no role exists
        Returns: empty List if no members are in role
        '''
        role = self.getRoleFromName(roleName, guild)
        if role == None:
            return None

        membersInRole = list()
        for member in guild.members:
            if role in member.roles:
                membersInRole.append(member)
        
        return membersInRole

            

    def registerChannel(self, channel:discord.TextChannel):
        self.channelDict[channel.guild.id] = channel.id
        self.save()

    def unregisterChannel(self, guild:discord.Guild):
        try:
            self.channelDict.pop(guild.id)
            self.save()
            return True
        except:
            return False

    def getRegisteredChannel(self, guild:discord.Guild):
        try:
            channelID = self.channelDict[guild.id]
            return guild.get_channel(channelID)
        except:
            return None