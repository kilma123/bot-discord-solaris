# ========= bot.py =========
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from datetime import datetime

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========= CONFIGURAÇÕES =========
# Canal de cargos
CANAL_CARGOS_ID = 1451661628926988414

# Sistema de Tickets
CATEGORIA_TICKETS_ID = 1448826991586574377
CANAL_TICKETS_ID = 1448826991586574378
CANAL_LOGS_ID = 1448826991406092367

# IDs dos cargos de Staff
CARGOS_STAFF = [
    1448826990034419713,
    1452786608146354320,
    1451695585856848051,
    1451695626449457232,
    1451695664206577827
]

MENSAGEM_CARGOS_ID = None
MENSAGEM_TICKETS_ID = None

CARGOS = {
    "🇧🇷": "🇧🇷 Brasil",
    "🇵🇹": "🇵🇹 Portugal",
    "🇺🇸": "🇺🇸 Estados Unidos",
    "🇫🇷": "🇫🇷 França",
    "🇪🇸": "🇪🇸 Espanha"
}

# Tipos de tickets
TIPOS_TICKETS = {
    "ajuda": {"emoji": "❓", "nome": "Ajuda Geral", "cor": discord.Color.blue()},
    "suporte": {"emoji": "🛠️", "nome": "Suporte Técnico", "cor": discord.Color.orange()},
    "denuncia": {"emoji": "⚠️", "nome": "Denúncia", "cor": discord.Color.red()},
    "resgate": {"emoji": "🎁", "nome": "Resgate de Itens", "cor": discord.Color.green()},
    "parceria": {"emoji": "🤝", "nome": "Parcerias", "cor": discord.Color.purple()}
}

tickets_abertos = {}

# ========= SISTEMA DE CARGOS E TICKETS =========
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)

    if not member:
        return

    emoji = str(payload.emoji)

    # Sistema de cargos
    if payload.message_id == MENSAGEM_CARGOS_ID:
        if emoji not in CARGOS:
            return

        role = discord.utils.get(guild.roles, name=CARGOS[emoji])
        if role:
            await member.add_roles(role)
            print(f"➕ Cargo {role.name} adicionado a {member.name}")

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != MENSAGEM_CARGOS_ID:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)

    if not member:
        return

    emoji = str(payload.emoji)
    if emoji not in CARGOS:
        return

    role = discord.utils.get(guild.roles, name=CARGOS[emoji])
    if role:
        await member.remove_roles(role)
        print(f"➖ Cargo {role.name} removido de {member.name}")

# ========= FUNÇÕES AUXILIARES =========
def tem_cargo_staff(member: discord.Member) -> bool:
    """Verifica se o membro tem algum cargo de staff"""
    return any(role.id in CARGOS_STAFF for role in member.roles)

async def enviar_log(guild: discord.Guild, embed: discord.Embed):
    """Envia log para o canal de logs"""
    canal_logs = guild.get_channel(CANAL_LOGS_ID)
    if canal_logs:
        await canal_logs.send(embed=embed)

# ========= SISTEMA DE TICKETS =========
async def criar_ticket(member: discord.Member, guild: discord.Guild, tipo: str):
    # Verifica se já tem ticket aberto
    if member.id in tickets_abertos:
        try:
            canal_existente = guild.get_channel(tickets_abertos[member.id])
            if canal_existente:
                await member.send(f"❌ Você já tem um ticket aberto: {canal_existente.mention}")
                return
        except:
            pass

    categoria = guild.get_channel(CATEGORIA_TICKETS_ID)
    if not categoria:
        await member.send("❌ Categoria de tickets não encontrada!")
        return

    info_ticket = TIPOS_TICKETS[tipo]
    
    # Permissões do canal
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(
            read_messages=True, 
            send_messages=True,
            attach_files=True,
            embed_links=True
        ),
        guild.me: discord.PermissionOverwrite(
            read_messages=True, 
            send_messages=True,
            manage_channels=True,
            manage_messages=True
        )
    }

    # Adiciona permissões para os cargos de staff
    for cargo_id in CARGOS_STAFF:
        cargo = guild.get_role(cargo_id)
        if cargo:
            overwrites[cargo] = discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True
            )

    # Cria o canal do ticket
    canal_ticket = await categoria.create_text_channel(
        name=f"{info_ticket['emoji']}-{tipo}-{member.name}",
        overwrites=overwrites,
        topic=f"Ticket de {info_ticket['nome']} | Aberto por {member.name} ({member.id})"
    )

    tickets_abertos[member.id] = canal_ticket.id

    # Embed inicial do ticket
    embed = discord.Embed(
        title=f"{info_ticket['emoji']} {info_ticket['nome']}",
        description=(
            f"Olá {member.mention}!\n\n"
            f"**Tipo do ticket:** {info_ticket['nome']}\n"
            f"**Aberto em:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
            f"Nossa equipe de suporte responderá em breve.\n"
            f"Por favor, descreva detalhadamente seu problema ou solicitação."
        ),
        color=info_ticket['cor']
    )
    embed.set_footer(text="Apenas staff pode fechar este ticket")
    embed.set_thumbnail(url=member.display_avatar.url)

    view = TicketView(member.id)
    await canal_ticket.send(f"{member.mention} - Ticket criado!", embed=embed, view=view)

    # Log de abertura
    log_embed = discord.Embed(
        title="🎫 Novo Ticket Aberto",
        color=discord.Color.green()
    )
    log_embed.add_field(name="Usuário", value=f"{member.mention} ({member.name})", inline=True)
    log_embed.add_field(name="Tipo", value=info_ticket['nome'], inline=True)
    log_embed.add_field(name="Canal", value=canal_ticket.mention, inline=True)
    log_embed.add_field(name="Data/Hora", value=datetime.now().strftime('%d/%m/%Y às %H:%M'), inline=False)
    log_embed.set_thumbnail(url=member.display_avatar.url)
    
    await enviar_log(guild, log_embed)
    
    print(f"🎫 Ticket {tipo} criado para {member.name} no canal {canal_ticket.name}")

class TicketButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ajuda Geral", style=discord.ButtonStyle.primary, emoji="❓", custom_id="ticket_ajuda")
    async def ajuda_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await criar_ticket(interaction.user, interaction.guild, "ajuda")
        await interaction.followup.send("✅ Ticket de ajuda criado! Verifique os canais.", ephemeral=True)

    @discord.ui.button(label="Suporte Técnico", style=discord.ButtonStyle.primary, emoji="🛠️", custom_id="ticket_suporte")
    async def suporte_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await criar_ticket(interaction.user, interaction.guild, "suporte")
        await interaction.followup.send("✅ Ticket de suporte criado! Verifique os canais.", ephemeral=True)

    @discord.ui.button(label="Denúncia", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="ticket_denuncia")
    async def denuncia_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await criar_ticket(interaction.user, interaction.guild, "denuncia")
        await interaction.followup.send("✅ Ticket de denúncia criado! Verifique os canais.", ephemeral=True)

    @discord.ui.button(label="Resgate de Itens", style=discord.ButtonStyle.success, emoji="🎁", custom_id="ticket_resgate")
    async def resgate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await criar_ticket(interaction.user, interaction.guild, "resgate")
        await interaction.followup.send("✅ Ticket de resgate criado! Verifique os canais.", ephemeral=True)

    @discord.ui.button(label="Parcerias", style=discord.ButtonStyle.secondary, emoji="🤝", custom_id="ticket_parceria")
    async def parceria_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await criar_ticket(interaction.user, interaction.guild, "parceria")
        await interaction.followup.send("✅ Ticket de parceria criado! Verifique os canais.", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="fechar_ticket")
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica se tem permissão (apenas staff)
        if not tem_cargo_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas membros da staff podem fechar tickets!", ephemeral=True)
            return

        # Pega informações antes de fechar
        canal = interaction.channel
        guild = interaction.guild
        membro = guild.get_member(self.user_id)
        
        # Log de fechamento
        log_embed = discord.Embed(
            title="🔒 Ticket Fechado",
            color=discord.Color.red()
        )
        log_embed.add_field(name="Ticket de", value=f"{membro.mention if membro else 'Usuário desconhecido'}", inline=True)
        log_embed.add_field(name="Fechado por", value=f"{interaction.user.mention}", inline=True)
        log_embed.add_field(name="Canal", value=canal.name, inline=True)
        log_embed.add_field(name="Data/Hora", value=datetime.now().strftime('%d/%m/%Y às %H:%M'), inline=False)
        
        await enviar_log(guild, log_embed)

        await interaction.response.send_message("🔒 Ticket será fechado em 5 segundos...", ephemeral=False)
        await asyncio.sleep(5)
        
        # Remove do dicionário
        if self.user_id in tickets_abertos:
            del tickets_abertos[self.user_id]
        
        await canal.delete()
        print(f"🔒 Ticket fechado por {interaction.user.name}")

# ========= COMANDOS SLASH =========
@bot.tree.command(name="setup_cargos", description="Configura o sistema de cargos automáticos")
@app_commands.checks.has_permissions(administrator=True)
async def setup_cargos(interaction: discord.Interaction):
    global MENSAGEM_CARGOS_ID
    
    canal = interaction.guild.get_channel(CANAL_CARGOS_ID)
    if not canal:
        await interaction.response.send_message("❌ Canal de cargos não encontrado!", ephemeral=True)
        return

    async for msg in canal.history(limit=50):
        if msg.author == bot.user:
            await msg.delete()

    texto = (
        "🌞 **Seja muito bem-vindo(a) ao nosso projeto!**\n\n"
        "Este espaço está sendo construído com cuidado, transparência "
        "e a participação da comunidade.\n\n"
        "👉 **Reaja abaixo com o idioma de sua preferência** "
        "para liberar o acesso aos conteúdos do servidor.\n\n"
        "🇧🇷 Português (Brasil)\n"
        "🇵🇹 Português (Portugal)\n"
        "🇺🇸 English (USA)\n"
        "🇫🇷 Français\n"
        "🇪🇸 Español\n\n"
        "_Seja muito bem-vindo(a) a esse nosso pequeno projeto 🚀_"
    )

    msg = await canal.send(texto)

    for emoji in CARGOS:
        await msg.add_reaction(emoji)

    MENSAGEM_CARGOS_ID = msg.id
    await interaction.response.send_message(f"✅ Sistema de cargos configurado no canal {canal.mention}!", ephemeral=True)
    print(f"✅ Sistema de cargos configurado. ID da mensagem: {MENSAGEM_CARGOS_ID}")

@bot.tree.command(name="setup_tickets", description="Configura o sistema de tickets")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    global MENSAGEM_TICKETS_ID
    
    canal = interaction.guild.get_channel(CANAL_TICKETS_ID)
    if not canal:
        await interaction.response.send_message("❌ Canal de tickets não encontrado!", ephemeral=True)
        return

    async for msg in canal.history(limit=50):
        if msg.author == bot.user:
            await msg.delete()

    embed = discord.Embed(
        title="🎫 Sistema de Tickets",
        description=(
            "**Precisa de ajuda? Abra um ticket!**\n\n"
            "Clique em um dos botões abaixo de acordo com sua necessidade:\n\n"
            "❓ **Ajuda Geral** - Dúvidas sobre o servidor\n"
            "🛠️ **Suporte Técnico** - Problemas técnicos\n"
            "⚠️ **Denúncia** - Reportar usuários ou conteúdo\n"
            "🎁 **Resgate de Itens** - Solicitar resgates\n"
            "🤝 **Parcerias** - Propostas de parceria\n\n"
            "**Cada usuário pode ter apenas 1 ticket aberto por vez.**\n"
            "**Apenas a staff pode fechar tickets.**"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Clique em um botão para abrir seu ticket!")

    view = TicketButtonsView()
    msg = await canal.send(embed=embed, view=view)
    
    # Fixa a mensagem
    try:
        await msg.pin()
        print("✅ Mensagem fixada com sucesso!")
    except Exception as e:
        print(f"⚠️ Não foi possível fixar a mensagem: {e}")

    MENSAGEM_TICKETS_ID = msg.id
    await interaction.response.send_message(
        f"✅ Sistema de tickets configurado e fixado no canal {canal.mention}!",
        ephemeral=True
    )
    print(f"✅ Sistema de tickets configurado. ID da mensagem: {MENSAGEM_TICKETS_ID}")

@bot.tree.command(name="criar_cargos", description="Cria automaticamente os cargos necessários")
@app_commands.checks.has_permissions(administrator=True)
async def criar_cargos(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    cargos_criados = []
    cargos_existentes = []

    for emoji, nome_cargo in CARGOS.items():
        role = discord.utils.get(interaction.guild.roles, name=nome_cargo)
        
        if not role:
            role = await interaction.guild.create_role(name=nome_cargo, mentionable=True)
            cargos_criados.append(nome_cargo)
        else:
            cargos_existentes.append(nome_cargo)

    resposta = "**Resultado:**\n"
    if cargos_criados:
        resposta += f"✅ Cargos criados: {', '.join(cargos_criados)}\n"
    if cargos_existentes:
        resposta += f"ℹ️ Cargos já existentes: {', '.join(cargos_existentes)}"

    await interaction.followup.send(resposta, ephemeral=True)

# ========= BOT ONLINE =========
@bot.event
async def on_ready():
    print("=" * 50)
    print("✅ Bot online!")
    print(f"📛 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📊 Servidores: {len(bot.guilds)}")
    print("=" * 50)

    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados")
    except Exception as e:
        print(f"⚠️ Erro ao sincronizar comandos: {e}")
    
    # Registra as views persistentes
    bot.add_view(TicketButtonsView())

# ========= TRATAMENTO DE ERROS =========
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Ocorreu um erro: {str(error)}", ephemeral=True)

# ========= INICIAR BOT =========
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")

    if not TOKEN:
        print("❌ ERRO: Token não encontrado!")
        exit(1)

    bot.run(TOKEN)
