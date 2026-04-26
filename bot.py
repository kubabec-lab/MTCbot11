import discord
from discord import app_commands
from discord.ext import commands
import os
import sqlite3
import random
from datetime import datetime

# --- KONFIGURACE ---
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_DIR = os.getenv('DATA_DIR', '/data')

WELCOME_CHANNEL_ID = 1466784809316782110
WARN_CHANNEL_ID = 1483168781080592474
TICKET_CATEGORY_ID = None  # ← SEM NAPIŠ ID KATEGORIE, do které se budou tickety vytvářet (nebo None = bez kategorie)

# --- TABULKA HODNOSTÍ ---
RANKS = [ ... ]  # (nechávám stejné jako měl)

# --- PERSISTENT DATABÁZE ---
DB_PATH = os.path.join(DATA_DIR, 'military_data.db')
db = sqlite3.connect(DB_PATH)
cursor = db.cursor()

# Vytvoření tabulek
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, xp INTEGER DEFAULT 0, warns INTEGER DEFAULT 0)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS tickets 
                  (ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER,
                   channel_id INTEGER,
                   reason TEXT,
                   created_at TEXT)''')
db.commit()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(RoleView())      # náborové tlačítko
        self.add_view(TicketView())    # ticket tlačítko
        await self.tree.sync()
        print("✅ MTC Systém + Ticket systém aktivován.")

    async def on_ready(self):
        print(f"🚀 Bot je online jako {self.user} | {datetime.now()}")

bot = MyBot()

# --- ERROR HANDLER ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    print(f"❌ Chyba: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message("Nastala chyba.", ephemeral=True)

# --- NÁBOROVÉ TLAČÍTKO (změněný vzhled) ---
class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vstoupit do armády", style=discord.ButtonStyle.primary, emoji="🪖", custom_id="mtc_verify_v4")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_private = interaction.guild.get_role(RANKS[0]['id'])
        if role_private in interaction.user.roles:
            return await interaction.response.send_message("⚠️ Už jsi v armádě!", ephemeral=True)
        
        await interaction.user.add_roles(role_private)
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (interaction.user.id,))
        db.commit()
        await interaction.response.send_message(f"✅ Vítej v MTC, vojáku! 🪖", ephemeral=True)

# --- TICKET SYSTÉM ---
class TicketModal(discord.ui.Modal, title="Vytvořit ticket"):
    reason = discord.ui.TextInput(label="Důvod ticketu", placeholder="Např. Nábor, Problém, Otázka...", style=discord.TextStyle.short, required=True)
    description = discord.ui.TextInput(label="Popis", placeholder="Podrobně popiš, s čím potřebuješ pomoct...", style=discord.TextStyle.long, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        # Vytvoření ticket kanálu
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None
        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        # Uložení do DB
        cursor.execute(
            "INSERT INTO tickets (user_id, channel_id, reason, created_at) VALUES (?, ?, ?, ?)",
            (interaction.user.id, channel.id, self.reason.value, datetime.now().isoformat())
        )
        db.commit()

        embed = discord.Embed(title="🎟️ Nový Ticket", color=discord.Color.blurple())
        embed.add_field(name="Uživatel", value=interaction.user.mention, inline=False)
        embed.add_field(name="Důvod", value=self.reason.value, inline=False)
        embed.add_field(name="Popis", value=self.description.value, inline=False)
        embed.set_footer(text=f"Ticket ID: {cursor.lastrowid}")

        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Ticket vytvořen! → {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vytvořit ticket", style=discord.ButtonStyle.blurple, emoji="📩", custom_id="create_ticket_v1")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- SLASH PŘÍKAZY ---
@bot.tree.command(name="ticketpanel", description="Pošle zprávu s tlačítkem pro vytvoření ticketu")
@app_commands.default_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎟️ Podpora / Nábor",
        description="Potřebuješ pomoct? Klikni na tlačítko níže a vytvoř ticket.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=TicketView())

# Zbytek kódu (on_message, check_rank_up, positions, profile) zůstává stejný jako v předchozí verzi.
# Pokud chceš, můžu ti poslat celý kompletní kód najednou.

bot.run(TOKEN)