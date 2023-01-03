#!/usr/bin/python3.8

from typing import List
import discord
from os import path
from argparse import ArgumentParser
import sys
import shlex
from botstate import *

from discord.ext import commands #Application Commands
#from discord_slash import SlashCommand, SlashContext


# Get command responses dir path
wd = path.abspath(__file__)
wd = path.dirname(wd)
commandResponseDir = path.join(wd, "command_responses")

stateFile = path.join(wd, "bot_state")
botState = BotState(stateFile)

# Set up script arg parser
scriptParser = ArgumentParser(description='''Discord Bot to allow users to self-administer roles on your server''')
scriptParser.add_argument('-t', '--token', metavar='tokenFile', dest='tokenFile', type=str, nargs=1, default=None, required=True,
                        help = "file to load OAuth2 token from")
args = scriptParser.parse_args()                        

intents = discord.Intents.default()
intents.members = True

# get the Discord bot bot
bot = commands.Bot(intents=intents, command_prefix='/')


### HELPERS ###
def parseMessage(message:str):
    '''Reads the Discord message and returns a list of arguments'''
    # test of this message is a valid command
    if not message.startswith(triggerChar):
        return None

    print("Parsing message: {}".format(message))
    slicedMessage = message[1:] # delete the trigger symbol
    parsedMessage = shlex.split(slicedMessage)
    print("Parsed: {}".format(parsedMessage))
    return parsedMessage

def getCommandResponse(fileName:str):
    '''
    Expects a file name in command_responses directory.
    Returns: the string contained in the specified file
    Returns: None if the specified file is not found
    '''

    # append .txt if it doesn't end with .txt already
    if not fileName.endswith(".txt"):
        fileName = fileName + ".txt"
    
    # grab the contents of the file
    filePath = path.join(commandResponseDir, fileName)
    try:
        with open(filePath, "r") as file:
            fileContents = file.read()
        # return the contents of the file
        return fileContents
    except:
        return "Error: file {} not found".format(fileName)

async def respondCommandNotFound(message:discord.message, commandArgs:List[str]):
    response = getCommandResponse("not_found").format("command", commandArgs[0].lower())
    await message.channel.send(response)

### EVENT HANDLERS ###
@bot.event
async def on_ready():
    print("Logged in as user {0.user} and ready to go!".format(bot))

### COMMANDS ###

# help
bot.remove_command('help') # remove default help command
@bot.command(name='help', aliases=['h'], brief='Show help text')
async def help_command(ctx, *, command: str = None):
    if command is None:
        # Send basic help text
        response = getCommandResponse("help")
        await ctx.send(response)
    else:
        # Attempt to send help text for the specified command
        response = getCommandResponse(f"help_{command.lower()}")
        if response is None: #TODO getCommandResponse never returns None. probably should fix getCommandResponse.
            response = getCommandResponse("not_found").format("help text for", command.lower())
        await ctx.send(response)
    
# ping
@bot.command(name='ping', brief='Ping the bot to check if it\'s alive')
async def ping_command(ctx):
    print("Responding to ping!")
    await ctx.send("pong")

# role TODO create a role menu which uses a Select Menu.
# This does not appear to be possible with the latest version of Python at the time of writing, 3.6.9
# @bot.command(name='role', aliases=['r'], brief='Assign roles to yourself')
# @commands.has_permissions(manage_roles=True)
# async def role_command(ctx):

# listroles l
@bot.command(name='listroles', aliases=['l'], brief='Lists self-assignable roles')
async def listroles_command(ctx):
    guild = ctx.guild
    if guild.id not in botState.roleDict:
        response = getCommandResponse("listroles_empty")
    else:
        response = getCommandResponse("listroles_header").format(bot.command_prefix, "add")
        response = response + "```"
        for roleName in botState.roleDict[guild.id]:
            response = response + "\n" + roleName# + " : " + str(botState.roleDict[roleName])
        response = response + "```"

    await ctx.send(response)

# listmembers
@bot.command(name='listmembers', brief='lists the members of a given role')
async def listroles_command(ctx, *, role_name:str = None):
    # check if an argument was provided
    if role_name == None:
        # if there was no argument provided, print help text and return.
        response = getCommandResponse("help_listmembers")
        await ctx.send(response)
        return
    
    # if there is an argument provided...
    guild = ctx.guild
    members_in_role = botState.getMembersInRoleName(role_name, guild)
    # Check if the role exists. If not, print role not found
    if members_in_role == None:
        response = getCommandResponse("not_found").format("role", role_name)
    # if the role exists but has no members, print listmembers empty text
    elif len(members_in_role) == 0:
        response = getCommandResponse("listmembers_empty").format(role_name)
    # Otherwise, the role has members; list them
    else:
        response = getCommandResponse("listmembers_header").format(role_name)
        response = response + "```"
        for member in members_in_role:
            response = response + "\n" + (member.nick or member.name)
        response = response + "```"

    # finally, send the message
    await ctx.send(response)

# add a
@bot.command(name='add', aliases=['a'], brief="Assign a role to yourself")
async def add_role_command(ctx, *, role_name:str = None):
    # Verify arguments
    if role_name == None:
        response = getCommandResponse("help_add")
        await ctx.send(response)
        return

    role = botState.getRoleFromName(role_name, ctx.guild)

    # if the given role does not exist, print not found text
    if role == None: # TODO this branch is never taken for some reason
        response = getCommandResponse("not_found").format("role", role_name)
    else:
        response = getCommandResponse("add").format(role_name)
        await ctx.author.add_roles(role)

    await ctx.send(response)

# remove r
@bot.command(name='remove', aliases=['r'], brief="Remove a role from yourself")
async def remove_role_command(ctx, *, role_name:str = None):
    # Verify arguments
    if role_name == None:
        response = getCommandResponse("help_remove")
        await ctx.send(response)
        return

    role = botState.getRoleFromName(role_name, ctx.guild)

    # if the given role does not exist, print not found text
    if role == None:
        response = getCommandResponse("not_found").format("role", role_name)
    else:
        response = getCommandResponse("remove").format(role_name)
        await ctx.author.remove_roles(role)

    await ctx.send(response)

# myroles TODO add ability to search for roles of a specific member
@bot.command(name='myroles', brief="Print a list of my roles")
async def myroles_command(ctx):
    role_names = botState.getRoleNamesFromMember(ctx.author)
    if len(role_names) == 0:
        response = getCommandResponse("myroles_empty").format(bot.command_prefix, "add")
    else:
        response = getCommandResponse("myroles_header").format(bot.command_prefix, "add", "remove")
        response = response + "```"
        for role_name in role_names:
            response = response + "\n" + role_name# + " : " + str(botState.roleDict[roleName])
        response = response + "```"
    
    await ctx.send(response)

# createrole
@bot.command(name='createrole', brief="Creates a new bot-managed role")
async def createrole_command(ctx, *, role_name:str):
    # verify permissions
    if not ctx.author.guild_permissions.manage_roles:
        return

    # Verify arguments
    if role_name == None:
        response = getCommandResponse("help_createrole")
        await ctx.send(response)
        return
    
    if await botState.addRole(role_name, ctx.guild):
        response = getCommandResponse("createrole").format(role_name)
    else:
        response = getCommandResponse("already_exists").format("role", role_name)
    
    await ctx.send(response)

# deleterole TODO
@bot.command(name='deleterole', brief="Deletes an existing bot-managed role")
async def deleterole_command(ctx, *, role_name:str):
    # verify permissions
    if not ctx.author.guild_permissions.manage_roles:
        return

    # Verify arguments
    if role_name == None:
        response = getCommandResponse("help_deleterole")
        await ctx.send(response)
        return
    
    if await botState.deleteRole(role_name, ctx.guild):
        response = getCommandResponse("deleterole").format(role_name)
    else:
        response = getCommandResponse("not_found").format("role", role_name)
    await ctx.send(response)

### MAIN ###
def main():
    # get the token file path from argument parser
    tokenPath = args.tokenFile[0]

    # open and read the token file. 
    # Format is expected to be the token with any amount of leading or trailing whitespace.
    with open(tokenPath, 'r') as tokenFile:
        token = tokenFile.read().strip()

    # Finally, start the bot
    bot.run(token)

# wrapping my code in a main function makes the C programmer in me feel safe.
sys.exit(main())