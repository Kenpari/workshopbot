import json
import os
import dotenv
import discord
import requests

#create bot class
bot = discord.Bot()

#add a ready event for when the bot is logged in and active
@bot.event
async def on_ready():
    """Will print that the bot is ready on successful login, with username and 4-digit discord ID"""
    print(f"{bot.user} is ready and online!")

#Load workshop data from file
workshop_data = {}
with open("workshop_items.json", 'r', encoding='utf-8') as f:
    try:
        workshop_data = json.load(f)
    except json.JSONDecodeError:
        print("Unable to load workshop data from file.")

@bot.slash_command(name='add', description="Add Steam workshop IDs to a list of monitored mods.")
async def add_workshop_ids(ctx, *workshop_ids: int):
    """Slash command to add workshop IDs from a space-separated list of user-provided IDs
      to a JSON to be monitored"""
    for workshop_id in workshop_ids:
        if str(workshop_id) in workshop_data:
            continue
        workshop_data[str(workshop_id)] = ""
        with open('workshop_items.json', 'w', encoding='utf-8') as f:
            json.dump(workshop_data, f)
    await ctx.send("Workshop IDs added to the list.")

@bot.slash_command(name='remove',
                   description="Remove Steam workshop IDs to a list of monitored mods.")
async def remove_workshop_ids(ctx, *workshop_ids: int):
    """Slash command to remove workshop IDs from a space-separated list of user-provided
    IDs from the monitored JSON"""
    in_list = False
    for workshop_id in workshop_ids:
        if str(workshop_id) not in workshop_data:
            continue
        del workshop_data[str(workshop_id)]
        in_list = True
    if in_list:
        with open('workshop_items.json', 'w', encoding='utf-8') as f:
            json.dump(workshop_data, f)
        await ctx.send("Workshop IDs removed from the list.")
    else:
        await ctx.send("Given IDs were not found in the list.")

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
                print(recorded_update)
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

#Add command to check for updates for tracked mods
@bot.slash_command(name="checkupdates",
                   description="Check for updates to monitored Workshop items.")
async def check_updates(ctx):
    """Slash command to manually check for updates in monitored JSON"""
    updated = get_update_dates()
    if updated:
        await ctx.respond(f"Found updates for Workshop IDs: {', '.join(updated)}")
    else:
        await ctx.respond("No updates found! Smooth sailing!")

#login with the bot's token
dotenv.load_dotenv()
TOKEN = str(os.getenv('TOKEN'))
bot.run(TOKEN)
