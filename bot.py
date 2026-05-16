import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import random
import math
import re

# --- KONFIGURACE ---
TOKEN = os.getenv('TOKEN')
WELCOME_CHANNEL_ID = 1466784809316782110
WARN_CHANNEL_ID = 1483168781080592474

# --- TABULKA HODNOSTÍ S LIMITAMY ---
RANKS = [
    {"name": "Private", "id": 1467194169423433738, "xp": 0, "limit": 999},
    {"name": "Deputy Corporal", "id": 1466792881800085555, "xp": 100, "limit": 10},
    {"name": "Corporal", "id": 1466792838527193243, "xp": 200, "limit": 7},
    {"name": "⭐Deputy Sergeant", "id": 1466792645014720602, "xp": 300, "limit": 4},
    {"name": "⭐Sergeant⭐", "id": 1466792531734958080, "xp": 400, "limit": 1},
    {"name": "⭐⭐Deputy commander⭐⭐", "id": 1466791815943557180, "xp": 500, "limit": 2},
    {"name": "⭐⭐Commander⭐⭐", "id": 1466791510451421244, "xp": 600, "limit": 2},
    {"name": "⭐⭐⭐ Deputy General⭐⭐⭐", "id": 1466788653203460146, "xp": 700, "limit": 1}
]

# --- DATABÁZE ---
db = sqlite3.connect('military_data.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, xp INTEGER DEFAULT 0, warns INTEGER DEFAULT 0, events_attended INTEGER DEFAULT 0)''')
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(RoleView())
        await self.tree.sync()
        print("✅ MILITARYBOT: Python verze s novým UI spuštěna.")

bot = MyBot()

# --- VERIFIKAČNÍ SYSTÉM (TLAČÍTKO) ---
class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vstoupit do armády", style=discord.ButtonStyle.green, custom_id="mtc_verify_py_v1")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_private = interaction.guild.get_role(RANKS[0]['id'])
        if role_private in interaction.user.roles:
            return await interaction.response.send_message("⚠️ Už jsi v armádě!", ephemeral=True)
        
        await interaction.user.add_roles(role_private)
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Vítej v MTC! Hodnost Private udělena.", ephemeral=True)

# --- POMOCNÉ FUNKCE (XP & BALISTIKA) ---
def add_xp(user_id, amount):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id))
    db.commit()
    cursor.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

async def check_rank_up(member, current_xp):
    for rank in reversed(RANKS):
        if current_xp >= rank['xp']:
            role = member.guild.get_role(rank['id'])
            if not role or role in member.roles: continue
            if len(role.members) < rank['limit']:
                await member.add_roles(role)
                channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
                if channel:
                    await channel.send(f"🎖️ **POVÝŠENÍ V POLI!** {member.mention} získal hodnost **{rank['name']}**!")
                break

def calculate_artillery(message_text):
    numbers = re.findall(r'\d+', message_text)
    if len(numbers) >= 2:
        offset = float(numbers[0])
        distance = float(numbers[1])
        if distance > 0:
            radians = math.atan(offset / distance)
            degrees = math.degrees(radians)
            mrad = radians * 1000
            return (f"🎯 **MILITARYBOT BALISTICKÁ JEDNOTKA:**\n"
                    f"Korekce: **{offset}m** | Vzdálenost: **{distance}m**\n"
                    f"🔹 Úhel posunu: **{degrees:.2f}°**\n"
                    f"🔹 Miliradiány: **{mrad:.1f} mrad**")
    return None

def get_tactical_advice(content):
    content = content.lower()
    if "cqb" in content:
        return "🏠 **TAKTIKA CQB:** Čistěte místnosti metodou 'Slicing the pie'. Pointman nikdy nezastavuje ve dveřích (Fatal Funnel)!"
    if "formace" in content or "formation" in content:
        return "🛡️ **FORMACE:** Line pro plnou palbu vpřed, Column pro rychlý přesun, Diamond pro kruhovou obranu velitele."
    if "pruzkum" in content or "recon" in content:
        return "🔭 **PRŮZKUM:** Zůstaň skrytý, podej hlášení o počtu a technice nepřítele, ale nevyvolávej boj bez rozkazu."
    return None

# --- CHATOVÝ MOZEK & XP ---
@bot.event
async def on_message(message):
    if message.author.bot: return

    # Taktika a Výpočty při označení
    if bot.user.mentioned_in(message):
        async with message.channel.typing():
            art_calc = calculate_artillery(message.content)
            tac_advice = get_tactical_advice(message.content)
            
            if art_calc: await message.reply(art_calc)
            elif tac_advice: await message.reply(tac_advice)
            else: await message.reply("Vojáku, hlásím připravenost. Zeptej se mě na taktiku nebo zadej dělostřelecká data! 🫡")

    # Přičtení XP
    new_xp = add_xp(message.author.id, random.randint(1, 3))
    if new_xp % 15 == 0: await check_rank_up(message.author, new_xp)
    await bot.process_commands(message)

# --- SLASH PŘÍKAZY S POKROČILÝM UI ---

@bot.tree.command(name="profile", description="Zobrazí tvou vojenskou kartu s detailním UI")
async def profile(interaction: discord.Interaction, vojak: discord.Member = None):
    target = vojak or interaction.user
    
    cursor.execute("SELECT xp, warns, events_attended FROM users WHERE user_id = ?", (target.id,))
    data = cursor.fetchone()
    xp, warns, events = (data[0], data[1], data[2]) if data else (0, 0, 0)
    
    current_rank = "Rekrut"
    for rank in RANKS:
        role = target.guild.get_role(rank['id'])
        if role and role in target.roles: current_rank = rank['name']

    # EMBED 1: Osobní data (Žlutý pruh)
    embed_profile = discord.Embed(title=f"🪖 {target.username}'s Profile", color=discord.Color.from_rgb(230, 195, 0))
    embed_profile.add_field(name="Username", value=target.username, inline=True)
    embed_profile.add_field(name="User ID", value=str(target.id), inline=True)
    embed_profile.add_field(name="Contact", value=target.mention, inline=False)
    embed_profile.set_thumbnail(url=target.display_avatar.url)

    # EMBED 2: Informace o hodnosti (Zelený pruh)
    embed_rank = discord.Embed(title="Rank Information", color=discord.Color.from_rgb(46, 204, 113))
    embed_rank.add_field(name="MTC Rank", value=current_rank, inline=True)
    embed_rank.add_field(name="Current Progress", value=f"⭐ **{xp} XP**", inline=True)

    # EMBED 3: Aktivita / Akce (Modrý pruh)
    embed_quota = discord.Embed(title="Quota Information", color=discord.Color.from_rgb(52, 152, 219))
    status = "🟢 Complete" if events >= 3 else "🔴 Incomplete"
    embed_quota.add_field(name="Quota Status", value=status, inline=False)
    embed_quota.add_field(name="Events Attended", value=str(events), inline=True)

    # EMBED 4: Tresty a Striky (Červený pruh)
    embed_strike = discord.Embed(title="Strike Information", color=discord.Color.from_rgb(231, 76, 60))
    if warns > 0:
        embed_strike.description = f"⚠️ Tento uživatel má aktivní prohřešky: **{warns}x Warn**."
    else:
        embed_strike.description = "This user has no active or expired strikes."

    # Odešleme všechny 4 embedy najednou spojené pod sebe
    await interaction.response.send_message(embeds=[embed_profile, embed_rank, embed_quota, embed_strike])

@bot.tree.command(name="add_event", description="Přidá vojákovi účast na akci (+1 Event)")
@app_commands.checks.has_permissions(administrator=True)
async def add_event(interaction: discord.Interaction, vojak: discord.Member):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (vojak.id,))
    cursor.execute("UPDATE users SET events_attended = events_attended + 1 WHERE user_id = ?", (vojak.id,))
    db.commit()
    await interaction.response.send_message(f"✅ Účast na akci úspěšně připsána uživateli {vojak.mention}.")

@bot.tree.command(name="positions", description="Volná místa v jednotkách")
async def positions(interaction: discord.Interaction):
    embed = discord.Embed(title="📊 Obsazenost pozic MTC", color=discord.Color.blue())
    for rank in RANKS[1:]:
        role = interaction.guild.get_role(rank['id'])
        count = len(role.members) if role else 0
        embed.add_field(name=rank['name'], value=f"`{count}/{rank['limit']}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setup_nabor", description="Vytvoří náborový panel")
@app_commands.checks.has_permissions(administrator=True)
async def setup_nabor(interaction: discord.Interaction):
    embed = discord.Embed(title="Nátor MTC", description="Vstup do armády kliknutím na tlačítko níže!", color=discord.Color.green())
    await interaction.channel.send(embed=embed, view=RoleView())
    await interaction.response.send_message("Panel nasazen.", ephemeral=True)

@bot.tree.command(name="warn", description="Udělit warn")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, vojak: discord.Member, duvod: str):
    cursor.execute("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (vojak.id,))
    db.commit()
    channel = bot.get_channel(WARN_CHANNEL_ID)
    if channel:
        await channel.send(embed=discord.Embed(title="⚠️ WARN LOG", description=f"Voják: {vojak.mention}\nDůvod: {duvod}", color=discord.Color.red()))
    await interaction.response.send_message("✅ Disciplinární trest uložen.", ephemeral=True)

@bot.tree.command(name="meeting", description="Svolat nástup")
@app_commands.checks.has_permissions(administrator=True)
async def meeting(interaction: discord.Interaction, cas: str):
    await interaction.response.send_message(f"📢 **@everyone POZOR!** Nástup v **{cas}**!", allowed_mentions=discord.AllowedMentions(everyone=True))

@bot.event
async def on_ready():
    print(f'--- {bot.user.name} připraven k boji ---')

bot.run(TOKEN)
