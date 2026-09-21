import os
import requests
from flask import Flask, request

app = Flask(__name__)

CLIENT_ID = "1548535889100013608"
CLIENT_SECRET = "MwRsptIpfzr9Dd1eg9qB5TgxuIgpKCff"
REDIRECT_URI = "https://distrito305-auth-web.onrender.com/callback"

@app.route("/")
def home():
    return "Servidor de Autenticación Activo", 200

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: No se proporcionó el código de verificación.", 400
    return "¡Verificación completada con éxito! Ya puedes cerrar esta ventana.", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)