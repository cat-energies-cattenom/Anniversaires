import os
import json
import datetime
import smtplib
import requests
import urllib.request
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 1. Chargement de la configuration personnalisable
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 2. Variables d'environnement récupérées depuis GitHub Secrets
PAHEKO_URL = os.environ['PAHEKO_URL'].rstrip('/')
PAHEKO_USER = os.environ['PAHEKO_USER']
PAHEKO_PASSWORD = os.environ['PAHEKO_PASSWORD']

SMTP_SERVER = os.environ['SMTP_SERVER']
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ['SMTP_USER']
SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', SMTP_USER)

# 3. Récupération de la date du jour (MM-JJ)
today = datetime.date.today()
today_str = today.strftime("%m-%d")

def get_membres():
    """Récupère la liste des membres via l'API Paheko."""
    query = "SELECT prenom, mail_personnel, date_naissance FROM users WHERE mail_personnel IS NOT NULL AND date_naissance IS NOT NULL;"
    
    response = requests.post(
        f"{PAHEKO_URL}/api/sql",
        data={"sql": query},
        auth=(PAHEKO_USER, PAHEKO_PASSWORD)
    )
    
    if not response.ok:
        print("Erreur retournée par Paheko :", response.text)
        
    response.raise_for_status()
    data = response.json()
    
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data

def get_logo_base64():
    """Convertit le fichier logo.png local en chaîne Base64 pour l'intégrer dans le HTML."""
    if os.path.exists("logo.png"):
        try:
            with open("logo.png", "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                print("Logo local converti en Base64 avec succès.")
                return f"data:image/png;base64,{encoded}"
        except Exception as e:
            print(f"Erreur lors de la conversion du logo local : {e}")
            
    # Secours : tentative depuis l'URL dans config.json si logo.png n'est pas trouvé
    try:
        url_logo = config.get('url_logo', '')
        if "github.com" in url_logo and "/blob/" in url_logo:
            url_logo = url_logo.replace("/blob/", "/raw/")
        
        req = urllib.request.Request(url_logo, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            encoded = base64.b64encode(response.read()).decode('utf-8')
            print("Logo distant téléchargé et converti en Base64 avec succès.")
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        print(f"Avertissement : impossible d'obtenir le logo ({e})")
        
    return ""

def envoyer_email(destinataire, prenom):
    """Envoie le mail avec le logo codé en Base64 centré au-dessus du message."""
    msg = MIMEMultipart("alternative")
    msg['Subject'] = config['sujet']
    msg['From'] = SENDER_EMAIL
    msg['To'] = destinataire

    corps_personnalise = config['texte_html'].replace("{prenom}", prenom)
    logo_src = get_logo_base64()

    # Balise image uniquement si le logo a pu être chargé
    logo_html = f'<img src="{logo_src}" alt="Logo" width="140" border="0" style="display: block; margin: 0 auto; width: 140px; height: auto; outline: none; text-decoration: none;">' if logo_src else ''

    # Structure HTML sans pièce jointe, logo codé directement dans le HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin:0; padding:0; background-color:#ffffff; font-family: Arial, sans-serif; color: #333333;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed;">
            <tr>
                <td align="center" style="padding: 20px 10px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="600" style="width: 600px; border: 1px solid #e0e0e0; background-color: #ffffff; border-radius: 8px;">
                        <!-- Logo codé en HTML/Base64 centré -->
                        <tr>
                            <td align="center" valign="top" style="padding: 30px 25px 10px 25px;">
                                {logo_html}
                            </td>
                        </tr>
                        <!-- Contenu du message centré -->
                        <tr>
                            <td align="center" valign="top" style="padding: 15px 30px 30px 30px; font-size: 15px; line-height: 1.6; color: #333333; text-align: center;">
                                {corps_personnalise}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_content, "html"))

    # Envoi du message
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, destinataire, msg.as_string())

def main():
    membres = get_membres()
    count = 0
    
    for m in membres:
        if isinstance(m, dict):
            d_naissance = str(m.get('date_naissance', ''))
            email = m.get('mail_personnel')
            prenom = m.get('prenom', 'Adhérent')

            if d_naissance and email:
                if d_naissance.endswith(today_str) or today_str in d_naissance:
                    print(f"Envoi de l'anniversaire à {prenom} ({email})...")
                    envoyer_email(email, prenom)
                    count += 1

    print(f"Terminé. {count} mail(s) envoyé(s).")

if __name__ == "__main__":
    main()
