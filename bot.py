import os
import threading
import requests
from flask import Flask, request

import discord
from discord.ext import commands

# ==========================================
# Configuración y Variables de Entorno
# ==========================================
# Carga de credenciales desde variables de entorno para mayor seguridad
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID", "1548535889100013608")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://distrito305-auth-web.onrender.com/callback")

GUILD_ID = int(os.environ.get("GUILD_ID", "1251347313008082944"))
ROLE_ID = int(os.environ.get("ROLE_ID", "1251351119531892807"))
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "1251352358051221504"))

# ==========================================
# Servidor Web Flask (OAuth2 Webhook)
# ==========================================
app = Flask(__name__)

@app.route("/")
def home():
    return "Servidor de autenticación en línea."

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: No se recibió ningún código de autorización.", 400

    if not CLIENT_SECRET or not BOT_TOKEN:
        return "Error interno: Faltan variables de entorno (CLIENT_SECRET o BOT_TOKEN) en la configuración.", 500

    # 1. Intercambiar el código por un Access Token
    token_url = "https://discord.com/api/v10/oauth2/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_response = requests.post(token_url, data=payload, headers=headers)
    if token_response.status_code != 200:
        return f"Error al obtener token de Discord: {token_response.text}", 400

    token_json = token_response.json()
    access_token = token_json.get("access_token")

    # 2. Obtener la información del usuario autenticado
    user_url = "https://discord.com/api/v10/users/@me"
    user_headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(user_url, headers=user_headers)

    if user_response.status_code != 200:
        return f"Error al obtener datos del usuario: {user_response.text}", 400

    user_data = user_response.json()
    user_id = user_data.get("id")
    username = user_data.get("username")

    # 3. Asignar el Rol mediante la API de Discord usando el Bot Token
    add_role_url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}"
    bot_headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    role_response = requests.put(add_role_url, headers=bot_headers)

    if role_response.status_code in [200, 204]:
        # 4. Enviar notificación al canal de Logs
        log_url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"
        log_payload = {
            "embeds": [{
                "title": "✅ Usuario Verificado",
                "description": f"El usuario **{username}** (<@{user_id}>) se ha verificado exitosamente por OAuth2.",
                "color": 3066993
            }]
        }
        requests.post(log_url, json=log_payload, headers=bot_headers)

        return """
        <html>
            <body style="background-color: #2c2f33; color: white; font-family: Arial, sans-serif; text-align: center; padding-top: 50px;">
                <h1>¡Verificación Completada!</h1>
                <p>Se te ha asignado el rol en el servidor de Discord. Ya puedes cerrar esta ventana.</p>
            </body>
        </html>
        """
    else:
        return f"Error al asignar el rol en el servidor: {role_response.text}", 500

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# Cliente de Discord (Bot Slash Commands)
# ==========================================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

@bot.tree.command(name="panel_verificacion", description="Publica el panel de verificación OAuth2.")
async def panel_verificacion(interaction: discord.Interaction, canal: discord.TextChannel = None, imagen_url: str = None):
    oauth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={requests.utils.quote(REDIRECT_URI)}&response_type=code&scope=identify"

    embed = discord.Embed(
        title="Verificación de Distrito305",
        description="Haz clic en el botón de abajo para verificarte mediante OAuth2 y obtener acceso al servidor.",
        color=discord.Color.blue()
    )
    embed.set_author(name="DistritoBOT")
    if imagen_url:
        embed.set_image(url=imagen_url)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Verificarse por OAuth2",
        style=discord.ButtonStyle.link,
        url=oauth_url,
        emoji="🔗"
    ))

    target_channel = canal or interaction.channel
    await target_channel.send(embed=embed, view=view)
    await interaction.response.send_message("Panel publicado correctamente.", ephemeral=True)

@bot.tree.command(name="ping", description="Comprueba la latencia del bot.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! 🏓 ({round(bot.latency * 1000)}ms)", ephemeral=True)

# ==========================================
# Inicialización Principal
# ==========================================
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("ADVERTENCIA: No se encontró BOT_TOKEN. La web se ejecutará sola sin el bot de Discord activo.")
