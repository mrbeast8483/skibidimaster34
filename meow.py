import discord
from discord.ext import commands
import os
import zipfile
import re
from datetime import datetime
import aiohttp
import certifi
import gc

# Set up the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message handling in DMs

# Create the bot instance
bot = commands.Bot(command_prefix='/', intents=intents)

# Cache for storing usernames to avoid redundant API calls
username_cache = {}

# Global aiohttp session with limited connection pool
session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10))

# Whitelist file path
whitelist_file = 'whitelist.txt'

# Owner's user ID for whitelist management
OWNER_ID = 1288930520196972605

# Load the whitelist from a file
def load_whitelist():
    if os.path.exists(whitelist_file):
        with open(whitelist_file, 'r') as file:
            return set(line.strip() for line in file.readlines())
    return set()

# Save the whitelist to a file
def save_whitelist(whitelist):
    with open(whitelist_file, 'w') as file:
        for user_id in whitelist:
            file.write(f'{user_id}\n')

# Initialize whitelist
whitelist = load_whitelist()

@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')
    
    # Sync global commands
    try:
        await bot.tree.sync()
        print('Global slash commands have been synced.')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

# Helper function to extract logs from the zip file
def extract_zip(zip_filepath, extract_to):
    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

# Helper function to get the Roblox username from the user ID using aiohttp
async def get_roblox_username(user_id):
    # Check if the username is already in the cache
    if user_id in username_cache:
        return username_cache[user_id]

    try:
        async with session.get(f'https://users.roblox.com/v1/users/{user_id}', ssl=certifi.where()) as response:
            if response.status == 200:
                data = await response.json()
                username = data.get('name', 'Unknown')
                username_cache[user_id] = username
                return username
            else:
                username_cache[user_id] = 'Unknown'
                return 'Unknown'
    except Exception as e:
        print(f"Error retrieving username for User ID {user_id}: {e}")
        username_cache[user_id] = 'Unknown'
        return 'Unknown'

# Helper function for "Alt Checker" analysis (streaming file processing)
async def alt_checker(logs_folder):
    user_pattern = r'userid:\s*([^,\s]+)'
    timestamp_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)'
    user_data = []

    for root, _, files in os.walk(logs_folder):
        for file in files:
            if file.endswith('.txt') or file.endswith('.log'):
                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as log_file:
                    for line in log_file:
                        user_matches = re.findall(user_pattern, line)
                        timestamp_match = re.search(timestamp_pattern, line)
                        
                        if timestamp_match:
                            timestamp = timestamp_match.group(1)
                            formatted_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%B %d, %I:%M%p")
                            
                            for user_id in user_matches:
                                username = await get_roblox_username(user_id)
                                user_data.append(f"{username} - {formatted_timestamp}")
    # Trigger garbage collection
    gc.collect()
    return user_data

# Helper function for "FFlag Checker" analysis (streaming file processing)
async def fflag_checker(logs_folder):
    json_pattern = r'LoadClientSettingsFromLocal: "(.*?)"(?=\r?\n|\Z)'  # Correct JSON pattern
    user_pattern = r'userid:\s*([^,\s]+)'
    timestamp_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)'
    json_data = {}

    for root, _, files in os.walk(logs_folder):
        for file in files:
            if file.endswith('.log'):
                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as log_file:
                    for line in log_file:
                        json_matches = re.findall(json_pattern, line)
                        
                        for json_content in json_matches:
                            if json_content not in json_data:
                                json_data[json_content] = []

                            # Find occurrences (user IDs) in the line content
                            user_ids = re.findall(user_pattern, line)
                            timestamp_match = re.search(timestamp_pattern, line)
                            
                            if timestamp_match:
                                timestamp = timestamp_match.group(1)
                                formatted_timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%B %d, %I:%M%p")

                            # Record each user occurrence with username, log file name, and timestamp
                            for user_id in user_ids:
                                username = await get_roblox_username(user_id)
                                occurrence = f"{username} - {file} - {formatted_timestamp}"
                                json_data[json_content].append(occurrence)
    # Trigger garbage collection
    gc.collect()
    return json_data

# Define the /whitelist command
@bot.tree.command(name="whitelist", description="Add or remove a user from the whitelist.")
async def whitelist_command(interaction: discord.Interaction, user: discord.User, action: str):
    # Ensure the command is used by the owner
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if action.lower() not in ['add', 'remove']:
        await interaction.response.send_message("Invalid action. Use 'add' or 'remove'.", ephemeral=True)
        return

    global whitelist
    user_id = str(user.id)
    
    if action.lower() == 'add':
        whitelist.add(user_id)
        save_whitelist(whitelist)
        await interaction.response.send_message(f"User {user.mention} has been added to the whitelist.", ephemeral=True)
    elif action.lower() == 'remove':
        whitelist.discard(user_id)
        save_whitelist(whitelist)
        await interaction.response.send_message(f"User {user.mention} has been removed from the whitelist.", ephemeral=True)

# Define the /list command
@bot.tree.command(name="list", description="Show the current whitelist.")
async def list_command(interaction: discord.Interaction):
    if not whitelist:
        await interaction.response.send_message("The whitelist is currently empty.", ephemeral=True)
    else:
        whitelist_text = "\n".join(f"<@{user_id}>" for user_id in whitelist)
        await interaction.response.send_message(f"Whitelisted IDs:\n{whitelist_text}", ephemeral=True)

# Define the /analyze command
@bot.tree.command(name="analyze", description="Analyze a zip file containing logs.")
async def analyze(interaction: discord.Interaction, file: discord.Attachment):
    # Check if the user is whitelisted
    if str(interaction.user.id) not in whitelist:
        await interaction.response.send_message("You are not whitelisted to use this command.", ephemeral=True)
        return

    # Check if the command is in a DM or server
    context = "in a DM" if interaction.guild is None else "in the server"
    await interaction.response.defer()
    await interaction.followup.send(f"Analyzing logs {context}...", ephemeral=True)

    # Check if the uploaded file is a zip file
    if not file.filename.endswith('.zip'):
        await interaction.followup.send('Please upload a valid zip file.', ephemeral=True)
        return

    # Save the uploaded zip file
    zip_filename = file.filename
    zip_filepath = os.path.join(os.getcwd(), zip_filename)
    extract_path = os.path.join(os.getcwd(), 'extracted_logs')

    try:
        await file.save(zip_filepath)

        # Extract the zip file
        extract_zip(zip_filepath, extract_path)

        # Perform the analysis
        alt_logs = await alt_checker(extract_path)  # Use await here
        flag_logs = await fflag_checker(extract_path)  # Use await here

        # Format the "Alt Checker" output
        alt_output = "AltLogs:\n" + "\n".join(alt_logs) if alt_logs else "No user IDs found."
        alt_filename = 'AltLogs.txt'
        with open(alt_filename, 'w', encoding='utf-8') as alt_file:
            alt_file.write(alt_output)

        # Format the "FFlag Checker" output
        flag_output = "FlagLogs:\n"
        for json_data, occurrences in flag_logs.items():
            flag_output += f"\nJSON Data:\n{json_data}\nOccurrences:\n"
            for occurrence in set(occurrences):  # Use `set` to avoid duplicate entries
                flag_output += f"    - {occurrence}\n"

        flag_filename = 'FlagLogs.txt'
        with open(flag_filename, 'w', encoding='utf-8') as flag_file:
            flag_file.write(flag_output)

        # Send the output files as attachments
        await interaction.followup.send(files=[discord.File(alt_filename), discord.File(flag_filename)])

        # Clean up the output text files
        if os.path.exists(alt_filename):
            os.remove(alt_filename)
        if os.path.exists(flag_filename):
            os.remove(flag_filename)

    except Exception as e:
        await interaction.followup.send(f'An error occurred: {str(e)}')

    finally:
        # Clean up extracted files
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        if os.path.exists(extract_path):
            for root, dirs, files in os.walk(extract_path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(extract_path)

# Close the aiohttp session when the bot shuts down
@bot.event
async def on_shutdown():
    await session.close()

# Run the bot
bot.run(os.getenv('DISCORD_BOT_TOKEN'))
