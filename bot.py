import json
import os
import re
import dotenv
import requests
import discord
from discord.ext import tasks
from discord import default_permissions

#create bot class
bot = discord.Bot()

#load environmental variables
dotenv.load_dotenv()
TOKEN = str(os.getenv('TOKEN'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

#add command group for workshop mod monitoring-related commands
mods = bot.create_group(name = "mods",
                        description = "Commands related to monitored Workshop mods",
                        default_member_permissions = discord.Permissions(administrator = True))

#Load workshop data from file
workshop_data = {}
with open("workshop_items.json", 'r', encoding='utf-8') as f:
    try:
        workshop_data = json.load(f)
    except json.JSONDecodeError:
        print("Unable to load workshop data from file.")

@mods.command(
        name='add',
        description="Add Steam workshop IDs to a list of monitored mods.",
        options = [
            discord.Option(input_type = str,
                           name = "workshop_ids",
                           description="List of Workshop IDs to add to the monitored list, with spaces between each ID.")
        ])
async def add_workshop_ids(ctx, workshop_ids: str):
    """Slash command to add workshop IDs from a space-separated list of user-provided IDs
      to a JSON to be monitored"""
    try:
        assert re.match(r"^(?:\d\s?)*$", workshop_ids)
        for workshop_id in workshop_ids.split():
            if workshop_id in workshop_data:
                continue
            workshop_data[workshop_id] = ""
            with open('workshop_items.json', 'w', encoding='utf-8') as f:
                json.dump(workshop_data, f)
        await ctx.respond("Workshop IDs added to the list.")
    except AssertionError:
        await ctx.respond("There was a problem processing the provided list of IDs. Please make sure you are using the correct format.")

@mods.command(
        name='remove',
        description="Remove Steam workshop IDs to a list of monitored mods.",
        options = [
            discord.Option(input_type = str,
                           name = "workshop_ids",
                           description="List of Workshop IDs to remove from the monitored list, with spaces between each ID.")
        ])
async def remove_workshop_ids(ctx, workshop_ids: str):
    """Slash command to remove workshop IDs from a space-separated list of user-provided
    IDs from the monitored JSON"""
    try:
        assert re.match(r"^(?:\d\s?)*$", workshop_ids)
        in_list = False
        for workshop_id in workshop_ids.split():
            if workshop_id not in workshop_data:
                continue
            del workshop_data[workshop_id]
            in_list = True
        if in_list:
            with open('workshop_items.json', 'w', encoding='utf-8') as f:
                json.dump(workshop_data, f)
            await ctx.respond("Workshop IDs removed from the list.")
        else:
            await ctx.respond("Given IDs were not found in the list.")
    except AssertionError:
        await ctx.respond("There was a problem processing the provided list of IDs. Please make sure you are using the correct format.")

def get_update_dates():
    """Function to check update dates of mods in monitored JSON"""
    updated = []
    if workshop_data:
        num_items = len(workshop_data)
        url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
        data_dict = {'itemcount': num_items}
        data_dict.update({f"publishedfileids[{k}]":
                          v for k,v in zip(range(num_items),[int(v) for v in workshop_data])})
        response = requests.post(url, data_dict, timeout=1.5)
        data = json.loads(response.text)
        for workshop_id, pubfile in zip(workshop_data, data["response"]["publishedfiledetails"]):
            try:
                last_updated = pubfile["time_updated"]
                recorded_update = workshop_data[workshop_id]
                if recorded_update != '':
                    if recorded_update < last_updated:
                        updated.append(workshop_id)
                        workshop_data[workshop_id] = last_updated
                else:
                    workshop_data[workshop_id] = last_updated
            except KeyError:
                print(f"Error retrieving update date for Workshop ID {workshop_id}")
    with open('workshop_items.json', 'w', encoding='utf-8') as f:
        json.dump(workshop_data, f)
    return updated

@mods.command(name="checkupdates",
                   description="Check for updates to monitored Workshop items.")
async def check_updates(ctx):
    """Slash command to manually check for updates in monitored JSON"""
    updated = get_update_dates()
    if updated:
        await ctx.respond(f"Found updates for Workshop IDs: {', '.join(updated)}")
    else:
        await ctx.respond("No updates found! Smooth sailing!")

@mods.command(name="list",
                   description="View a list of all currently monitored workshop IDs.")
async def print_list(ctx):
    """Slash command to print a list of all currently monitored workshop IDs"""
    if workshop_data:
        await ctx.respond(
            f"All currently monitored Workshop IDs:\n{', '.join([i for i in workshop_data])}")
    else:
        await ctx.respond("No currently monitored items.")

@tasks.loop(minutes=10.0)
async def automated_update_check(update_channel: discord.channel):
    """Automatically scan for updates to monitored workshop items"""
    updated = get_update_dates()
    if updated:
        await update_channel.send(f"Found updates for Workshop IDs: {', '.join(updated)}")

@bot.event
async def on_ready():
    """Ready event for when the bot is logged in and active"""
    print(f"{bot.user} is ready and online!")
    update_channel = bot.get_channel(CHANNEL_ID)
    automated_update_check.start(update_channel)

#login with the bot's token
bot.run(TOKEN)
