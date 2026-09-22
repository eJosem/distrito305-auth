import os
import sqlite3
import threading
import requests
from flask import Flask, request
import discord
from discord.ext import commands, tasks
import yt_dlp

# ==========================================
# 1. Configuración de Intents y Bot
# ==========================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 2. Variables de Configuración y IDs
# ==========================================
GUILD_ID = 1279183377778937917              
ROL_TRABAJANDO_ID = 1548547466561855538    
ROL_VERIFICADO_ID = 1542604216474796066    
CANAL_BIENVENIDA_ID = 1542604218270228576  
CANAL_ESTADO_ID = 1542678626300858468      
CANAL_LOGS_ID = 1551759127322042369        

CLIENT_ID = "1548535889100013608"
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
REDIRECT_URI = "https://distrito305-auth-web.onrender.com/callback"

CFX_CODE = "5oozbea"                       
FIVEM_IP = "34.128.4.46"
BANNER_URL = "https://cdn.discordapp.com/attachments/1542762298995773512/1544973576405520484/C4EF066D-E2D3-413B-8FEF-E42CABAE9E4A.png"

# User-Agent personalizado obligatorio para evitar bloqueos por Cloudflare/Discord
CUSTOM_USER_AGENT = "DistritoBOTAuth/2.0 (https://distrito305-auth-web.onrender.com)"

# ==========================================
# 3. Base de datos SQLite
# ==========================================
conn = sqlite3.connect("fichajes.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS fichajes (
    user_id TEXT,
    entrada TEXT,
    salida TEXT
)""")
conn.commit()

# ==========================================
# 4. Servidor Web Flask (OAuth2 Callback)
# ==========================================
app = Flask(__name__)

@app.route("/")
def home():
    return "<h3>Servidor de Autenticación Distrito 305 RP Activo</h3>", 200

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "<h3>Error: No se recibió código de autorización.</h3>", 400

    if not CLIENT_SECRET or not BOT_TOKEN:
        return "<h3>Error: Faltan las variables CLIENT_SECRET o BOT_TOKEN en Render.</h3>", 500

    try:
        # A) Intercambiar el código por el Access Token
        payload = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
        headers_oauth = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": CUSTOM_USER_AGENT
        }

        token_res = requests.post("https://discord.com/api/v10/oauth2/token", data=payload, headers=headers_oauth)
        if token_res.status_code != 200:
            return f"<h3>Error al obtener token de Discord ({token_res.status_code}):</h3><pre>{token_res.text}</pre>", 400

        token_data = token_res.json()
        access_token = token_data.get("access_token")

        # B) Obtener la información del usuario (@me)
        user_headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": CUSTOM_USER_AGENT
        }
        user_res = requests.get("https://discord.com/api/v10/users/@me", headers=user_headers)
        if user_res.status_code != 200:
            return f"<h3>Error al obtener datos del usuario ({user_res.status_code}):</h3><pre>{user_res.text}</pre>", 400

        user_info = user_res.json()
        user_id = user_info.get("id")
        username = user_info.get("username")

        # C) Forzar unión al servidor y otorgar el rol de verificado
        bot_headers = {
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": CUSTOM_USER_AGENT
        }

        requests.put(
            f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}",
            json={"access_token": access_token},
            headers=bot_headers
        )

        requests.put(
            f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROL_VERIFICADO_ID}",
            headers=bot_headers
        )

        # D) Logs e IP
        ip_cliente = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_cliente:
            ip_cliente = ip_cliente.split(',')[0].strip()

        pais, ciudad = "Desconocido", "Desconocida"
        try:
            geo_res = requests.get(f"http://ip-api.com/json/{ip_cliente}", timeout=3).json()
            pais = geo_res.get("country", "Desconocido")
            ciudad = geo_res.get("city", "Desconocida")
        except Exception:
            pass

        embed_payload = {
            "embeds": [{
                "title": "🟢 Nueva Verificación Registrada (OAuth2)",
                "color": 3066993,
                "fields": [
                    {"name": "Usuario", "value": f"<@{user_id}> (`{username}`)", "inline": True},
                    {"name": "IP Registrada", "value": f"`{ip_cliente}`", "inline": True},
                    {"name": "Ubicación", "value": f"{ciudad}, {pais}", "inline": True}
                ]
            }]
        }

        requests.post(
            f"https://discord.com/api/v10/channels/{CANAL_LOGS_ID}/messages",
            json=embed_payload,
            headers=bot_headers
        )

        return "<h1 style='color:green; font-family:sans-serif; text-align:center; margin-top:50px;'>¡Verificación completada con éxito! Ya puedes volver a Discord.</h1>", 200

    except Exception as e:
        return f"<h3>Error interno en la autenticación:</h3><pre>{str(e)}</pre>", 500

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 5. Eventos y Tareas del Bot
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ Bot conectado correctamente como: {bot.user} (ID: {bot.user.id})")
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"⚡ ¡Éxito! Se sincronizaron {len(synced)} comandos de barra.")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

    if not actualizar_estado_fivem.is_running():
        actualizar_estado_fivem.start()

@tasks.loop(seconds=60)
async def actualizar_estado_fivem():
    canal = bot.get_channel(CANAL_ESTADO_ID)
    if not canal:
        return

    headers = {"User-Agent": CUSTOM_USER_AGENT}
    estado = "🔴 Offline"
    jugadores_online = 0
    jugadores_max = 64
    color = discord.Color.red()

    urls = [
        f"http://{FIVEM_IP}:30120/dynamic.json",
        f"http://{FIVEM_IP}:30120/players.json",
        f"https://frontend.cfx-services.net/api/servers/single/{CFX_CODE}"
    ]

    import aiohttp
    async with aiohttp.ClientSession(headers=headers) as session:
        for url in urls:
            try:
                async with session.get(url, timeout=4) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        estado = "🟢 Online"
                        color = discord.Color.green()
                        if isinstance(data, dict):
                            if "Data" in data:
                                jugadores_online = data["Data"].get("clients", 0)
                                jugadores_max = data["Data"].get("sv_maxclients", 64)
                            else:
                                jugadores_online = data.get("clients", len(data.get("players", [])))
                        break
            except Exception:
                continue

    embed = discord.Embed(title="Distrito 305 RP", color=color)
    embed.set_author(name="DistritoBOT")
    embed.add_field(name="STATUS", value=f"```\n{estado}\n```", inline=True)
    embed.add_field(name="PLAYERS", value=f"```\n{jugadores_online}/{jugadores_max}\n```", inline=True)
    embed.add_field(name="F8 CONNECT", value=f"```\nconnect {FIVEM_IP}\n```", inline=False)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Actualizado cada minuto")

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Jugar", url=f"https://cfx.re/join/{CFX_CODE}", emoji="🚀"))

    mensajes_bot = []
    async for msg in canal.history(limit=15):
        if msg.author == bot.user and len(msg.embeds) > 0 and msg.embeds[0].title == "Distrito 305 RP":
            mensajes_bot.append(msg)

    if mensajes_bot:
        await mensajes_bot[0].edit(embed=embed, view=view)
        for duplicado in mensajes_bot[1:]:
            try: await duplicado.delete()
            except: pass
    else:
        await canal.send(embed=embed, view=view)

@bot.event
async def on_member_join(member: discord.Member):
    canal = member.guild.get_channel(CANAL_BIENVENIDA_ID)
    if not canal:
        return
    embed = discord.Embed(
        title="🎉 Bienvenid@ a Distrito 305 RP",
        description=(
            f"👋 Bienvenid@ {member.mention} a **Distrito 305 RP**\n\n"
            "📚 No olvides revisar las **#📚| normativas**\n"
            "📝 Si buscas postularte, dirígete a **#📝| formulario-escrito**\n\n"
            "✨ ¡Esperamos que disfrutes tu estadía en la ciudad!"
        ),
        color=discord.Color.from_str("#0000ff")
    )
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Distrito 305 RP")
    await canal.send(embed=embed)

# ==========================================
# 6. Comandos Slash
# ==========================================
class BotonPanelVerificacion(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        oauth_url = (
            f"https://discord.com/oauth2/authorize"
            f"?client_id={CLIENT_ID}"
            f"&response_type=code"
            f"&redirect_uri=https%3A%2F%2Fdistrito305-auth-web.onrender.com%2Fcallback"
            f"&scope=identify%20guilds.join"
        )
        self.add_item(discord.ui.Button(
            label="Verificarse por OAuth2",
            style=discord.ButtonStyle.link,
            url=oauth_url,
            emoji="🔗"
        ))

@bot.tree.command(name="panel_verificacion", description="Publica el panel de verificación con botón web")
async def panel_verificacion(interaction: discord.Interaction, canal: discord.TextChannel = None, imagen_url: str = None):
    await interaction.response.defer(ephemeral=True)
    try:
        canal_destino = canal or interaction.channel
        embed = discord.Embed(
            title="Verificación de Distrito 305 RP",
            description="Haz clic en el botón de abajo para autorizar la aplicación y verificar tu cuenta en el servidor.",
            color=discord.Color.blue()
        )
        embed.set_author(name="DistritoBOT")
        if imagen_url:
            embed.set_image(url=imagen_url)
        
        await canal_destino.send(embed=embed, view=BotonPanelVerificacion())
        await interaction.followup.send(f"✅ Panel enviado exitosamente a {canal_destino.mention}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al enviar el panel: {e}", ephemeral=True)

@bot.tree.command(name="ping", description="Comprueba la latencia del bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 ¡Pong! Latencia: {round(bot.latency * 1000)}ms")

# ==========================================
# 7. Punto de Entrada
# ==========================================
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("⚠️ Error: No se encontró la variable BOT_TOKEN.")
