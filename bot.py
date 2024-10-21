import discord
from discord import TextChannel
import os
import json
import feedparser
import re
from datetime import datetime

RSS_FEED_URL = "https://www.codeur.com/projects?format=rss"
PUBLISHED_PROJECTS_FILE = "published_projects.json"
TAGS_FILE = "tags.json"

intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)


def load_published_projects():
    if os.path.exists(PUBLISHED_PROJECTS_FILE):
        with open(PUBLISHED_PROJECTS_FILE, 'r') as file:
            return json.load(file)
    return []


def save_published_projects(published_projects):
    with open(PUBLISHED_PROJECTS_FILE, 'w') as file:
        json.dump(published_projects, file)


@client.event
async def on_ready():
    print(f'Barbe Noire est prêt')

    published_projects = load_published_projects()

    feed = feedparser.parse(RSS_FEED_URL)

    for entry in reversed(feed.entries):
        title = entry.title
        link = entry.link
        description = entry.description
        guid = entry.guid
        pub_date = entry.published

        if guid in published_projects:
            continue

        pub_date_dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')

        today = datetime.now(pub_date_dt.tzinfo).date()

        if pub_date_dt.date() != today:
            continue

        await send_rss_update(title, link, description, pub_date_dt)
        published_projects.append(guid)

    save_published_projects(published_projects)


def clean_description(html_description):
    # CDATA
    html_description = html_description.strip('<![CDATA[').strip(']]>')

    paragraphs = re.findall(r'<p>(.*?)</p>', html_description, re.DOTALL)

    for para in paragraphs:
        if 'Budget :' in para or 'Catégories :' in para or 'Voir ce projet sur Codeur' in para:
            continue
        else:
            clean_desc = para.strip()
            return clean_desc

    return ""


async def send_rss_update(title, link, description, pub_date_dt):
    clean_desc = clean_description(description)

    role_mentions = []
    channels = []
    guild = client.get_guild(int(os.getenv("GUILD_ID", "")))

    # Vérifiez si la guilde est valide
    if guild is None:
        print("Guild is None, unable to get roles or channels.")
        return

    technologies = [
       
    ]

    for tag in TAGS:
        technologies.extend(TAGS[tag]["sub_tags"])

    for tech in technologies:
       
        pattern = r'\b' + re.escape(tech) + r'\b'
        if re.search(pattern, title.lower()) or re.search(pattern, clean_desc.lower()):
            
            tech_name = next((tag for tag in TAGS if tech in TAGS[tag]["sub_tags"]), None)
          
            role_id = TAGS[tech_name]["role_id"]

            if role_id:
                role = guild.get_role(int(role_id))
                if role:
                    role_mentions.append(role.mention)

            channel_id = os.getenv(f"{tech.upper()}_CHANNEL_ID")
            if channel_id:
                try:
                    channel = client.get_channel(int(channel_id))
                    if isinstance(channel, TextChannel):  # Vérifiez si c'est un TextChannel
                        channels.append(channel)
                    else:
                        print(f"{tech.upper()}_CHANNEL_ID is not a TextChannel.")
                except ValueError:
                    print(f"Invalid channel ID for {tech.upper()}")
            else:
                print(f"{tech.upper()}_CHANNEL_ID environment variable is not set.")

    budget = None
    categories = None

    if "Budget" in description:
        budget_start = description.find("Budget :") + len("Budget :")
        budget_end = description.find("€", budget_start) + 1
        budget = description[budget_start:budget_end].strip()

    if "Catégories" in description:
        categories_start = description.find("Catégories :") + len(
            "Catégories :")
        categories_end = description.find("</p>", categories_start)
        categories = description[categories_start:categories_end].strip()

    time_since_published = discord.utils.format_dt(pub_date_dt, 'R')

    embed = discord.Embed(title=title, description=clean_desc, color=0x3498db)

    if budget:
        embed.add_field(name="Budget", value=budget, inline=True)
    if categories:
        embed.add_field(name="Catégories", value=categories, inline=True)
    embed.add_field(name="Voir l'annonce",
                    value=f"[Clique ici]({link})",
                    inline=True)
    embed.add_field(name="Publié", value=time_since_published, inline=False)

    all_channel = client.get_channel(int(os.getenv("ALL_CHANNEL_ID", "")))

    if isinstance(all_channel, discord.TextChannel):
        await all_channel.send(embed=embed)
    else:
        print("The channel is not a TextChannel and cannot send messages.")

    for channel in channels:
        if role_mentions:
            await channel.send(' '.join(role_mentions), embed=embed)
        else:
            await channel.send(embed=embed)


client.run(os.getenv("TOKEN", ""))
