import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import random

# --- NASTAVENÍ ---
TOKEN = 'TVUJ_TOKEN_ZDE'  # Sem dej svůj nový Token v uvozovkách
WARN_CHANNEL_ID = 123456789  # Sem dej ID tvého kanálu #warny

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- VERIFIKAČNÍ SYSTÉM (Tlačítko na role) ---
class RoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Vstoupit do armády (Získat hodnost)", style=discord.ButtonStyle.green, custom_id="assign_rank")
    async def assign_rank(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Názvy rolí - musí být PŘESNĚ jako na Discordu
        role_private_name = "Private"
        role_deputy_name = "Deputy Corporal"
        
        role_private = discord.utils.get(interaction.guild.roles, name=role_private_name)
        role_deputy = discord.utils.get(interaction.guild.roles, name=role_deputy_name)

        if not role_private or not role_deputy:
            await interaction.response.send_message("Chyba: Role 'Private' nebo 'Deputy Corporal' neexistují!", ephemeral=True)
            return

        roles_to_add = [role_private]
        msg_text = f"Byl jsi přijat! Byla ti udělena hodnost **{role_private_name}**."

        # Šance 50/50 na Deputy Corporal
        if random.choice([True, False]):
            roles_to_add.append(role_deputy)
            msg_text += f" Navíc jsi byl jmenován do funkce **{role_deputy_name}**! 🎖️"

        try:
            await interaction.user.add_roles(*roles_to_add)
            await interaction.response.send_message(msg_text, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Chyba: Bot nemá práva spravovat role! (Posuň jeho roli v nastavení výš)", ephemeral=True)

# --- UDÁLOSTI ---
@bot.event
async def on_ready():
    bot.add_view(RoleView()) # Aby tlačítko fungovalo i po restartu
    print(f'MTC Bot připraven! Přihlášen jako {bot.user}')

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="chat")
    if channel:
        await channel.send(f"Pozor! Voják {member.mention} právě dorazil na základnu. Vítej!")

# --- PŘÍKAZY ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    embed = discord.Embed(
        title="Nábor do MTC", 
        description="Kliknutím na tlačítko níže se zapíšeš do aktivní služby.\n\n"
                    "• Každý obdrží hodnost **Private**.\n"
                    "• Můžeš být náhodně jmenován **Deputy Corporal**!", 
        color=discord.Color.dark_green()
    )
    await ctx.send(embed=embed, view=RoleView())

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, duvod="Neuveden"):
    warn_channel = bot.get_channel(WARN_CHANNEL_ID)
    embed = discord.Embed(title="⚠️ VAROVÁNÍ", color=discord.Color.red())
    embed.add_field(name="Uživatel:", value=member.mention, inline=False)
    embed.add_field(name="Důvod:", value=duvod, inline=False)
    embed.add_field(name="Udělil:", value=ctx.author.mention, inline=False)
    embed.set_footer(text=f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    if warn_channel:
        await warn_channel.send(embed=embed)
        await ctx.send(f"Voják {member.mention} byl nahlášen.")

@bot.command()
async def meeting(ctx, cas: str):
    await ctx.send(f"🎖️ **@everyone POZOR!** Nástup v **{cas}**!")

# --- SPUŠTĚNÍ ---
bot.run('MTQ5NjgzODEzODY4NzkxNDAxNQ.GgCjSV.1weQrNEA2g-f6_5jTer-C9iU0orHk4NI3KQKg4')
