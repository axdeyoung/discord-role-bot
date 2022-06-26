from typing import List
import discord
from os import path
from argparse import ArgumentParser
import sys
import shlex
from botstate import *

triggerChar = '$'


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

# get the Discord client
client = discord.Client()


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


### COMMAND RESPONSES ###
async def respondHelp(message:discord.Message, commandArgs:List[str]):
    if len(commandArgs) == 1: # if help used on its own
        print("Sending basic help text")
        response = getCommandResponse("help")
        await message.channel.send(response)
    else: # if one or more arguments are passed to help
        print("Attempting to send help text for {}".format(commandArgs[1]))
        # get help file of format "help_cmd.txt"
        response = getCommandResponse("help_{}".format(commandArgs[1].lower()))
        # if that message doesn't exist, give generic command not found text
        if response == None:
            response = getCommandResponse("not_found").format("help text for", commandArgs[1].lower())
        await message.channel.send(response)

async def respondCommandNotFound(message:discord.message, commandArgs:List[str]):
    response = getCommandResponse("not_found").format("command", commandArgs[0].lower())
    await message.channel.send(response)

async def listRoles(message:discord.message):
    guild = message.guild
    if guild.id not in botState.roleDict:
        response = getCommandResponse("listroles_empty")
    else:
        response = getCommandResponse("listroles_header").format(triggerChar, "add")
        response = response + "```"
        for roleName in botState.roleDict[guild.id]:
            response = response + "\n" + roleName# + " : " + str(botState.roleDict[roleName])
        response = response + "```"

    await message.channel.send(response)


async def createRole(message:discord.message, commandArgs:List[str]):
    response = None
    try:
        roleName = commandArgs[1]
    except:
        response = getCommandResponse("help_createrole")
        await message.channel.send(response)
        return

    if await botState.addRole(roleName, message.guild):
        response = getCommandResponse("createrole").format(roleName)
    else:
        response = getCommandResponse("already_exists").format("role", roleName)

    await message.channel.send(response)


async def deleteRole(message:discord.message, commandArgs:List[str]):
    response = None
    
    try:
        roleName = commandArgs[1]
    except:
        response = getCommandResponse("help_deleterole")
        await message.channel.send(response)
        return

    if await botState.deleteRole(roleName, message.guild):
        response = getCommandResponse("deleterole").format(roleName)
    else:
        response = getCommandResponse("not_found").format("role", roleName)
    await message.channel.send(response)

async def add(message:discord.message, commandArgs:List[str]):
    response = None
    try:
        roleName = commandArgs[1]
    except:
        response = getCommandResponse("help_add")
        await message.channel.send(response)
        return

    role = botState.getRoleFromName(roleName, message.guild)

    if role != None:
        response = getCommandResponse("add").format(roleName)
        member = message.author
        await member.add_roles(role)
    else:
        response = getCommandResponse("not_found").format("role", roleName)
    await message.channel.send(response)

async def remove(message:discord.message, commandArgs:List[str]):
    response = None
    try:
        roleName = commandArgs[1]
    except:
        response = getCommandResponse("help_remove")
        await message.channel.send(response)
        return

    role = botState.getRoleFromName(roleName, message.guild)

    if role != None:
        response = getCommandResponse("remove").format(roleName)
        member = message.author
        await member.remove_roles(role)
    else:
        response = getCommandResponse("not_found").format("role", roleName)
    await message.channel.send(response)

async def listMyRoles(message:discord.message, commandArgs:List[str]):
    # TODO add ability to search for a specified member
    roleNames = botState.getRoleNamesFromMember(message.author)
    if len(roleNames) == 0:
        response = getCommandResponse("myroles_empty").format(triggerChar, "add")
    else:
        response = getCommandResponse("myroles_header").format(triggerChar, "add", "remove")
        response = response + "```"
        for roleName in roleNames:
            response = response + "\n" + roleName# + " : " + str(botState.roleDict[roleName])
        response = response + "```"

    await message.channel.send(response)


async def registerChannel(message:discord.message, commandArgs:List[str]):
    response = None
    try:
        channelName = commandArgs[1]
    except:
        response = getCommandResponse("help_registerchannel")
        await message.channel.send(response)
        return
    
    guild = message.guild
    channel = discord.utils.get(guild.text_channels, name=channelName)
    if channel != None:
        response = getCommandResponse("registerchannel").format(channelName)
        botState.registerChannel(channel)
    else:
        response = getCommandResponse("not_found").format("channel", channelName)
    await message.channel.send(response)

async def unregisterChannel(message:discord.message):
    response = None
    guild = message.guild
    botState.unregisterChannel(guild)
    response = getCommandResponse("unregisterchannel")
    await message.channel.send(response)

### EVENT HANDLERS ###
@client.event
async def on_ready():
    print("Logged in as user {0.user} and ready to go!".format(client))

@client.event
async def on_message(message:discord.Message):
    # if the message is from me, ignore it.
    if message.author == client.user:
        return 
    # if the message is not a command, ignore it
    if not message.content.startswith(triggerChar):
        return

    # read message
    commandArgs = parseMessage(message.content)

    # respond to valid commands
    command = commandArgs[0].lower()

    if command == "ping":
        print("Ponging!")
        await message.channel.send('pong')
    
    elif command == "help" or command == "h":
        await respondHelp(message, commandArgs)

    elif command == "listroles" or command == "l":
        await listRoles(message)

    elif command == "add" or command == "a":
        await add(message, commandArgs)

    elif command == "remove" or command == "r":
        await remove(message, commandArgs)

    elif command == "myroles":
        await listMyRoles(message, commandArgs)

    elif command == "createrole" and message.author.guild_permissions.manage_roles:
        await createRole(message, commandArgs)
    
    elif command == "deleterole" and message.author.guild_permissions.manage_roles:
        await deleteRole(message, commandArgs)

    elif command == "registerchannel" and message.author.guild_permissions.manage_channels:
        await registerChannel(message, commandArgs)

    elif command == "unregisterchannel" and message.author.guild_permissions.manage_channels:
        await unregisterChannel(message)

    else:
        await respondCommandNotFound(message, commandArgs)

### MAIN ###
def main():
    # get the token file path from argument parser
    tokenPath = args.tokenFile[0]

    # open and read the token file. 
    # Format is expected to be the token with any amount of leading or trailing whitespace.
    with open(tokenPath, 'r') as tokenFile:
        token = tokenFile.read().strip()

    # Finally, start the client
    client.run(token)

# wrapping my code in a main function makes the C programmer in me feel safe.
sys.exit(main())