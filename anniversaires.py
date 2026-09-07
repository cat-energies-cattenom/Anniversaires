import os
import json
import datetime
import smtplib
import requests
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

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
    
    # Paheko renvoie parfois les résultats encapsulés dans une clé "results"
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data

def envoyer_email(destinataire, prenom):
    """Envoie le mail avec structure HTML compatible Outlook et logo embarqué."""
    msg = MIMEMultipart("related")
    msg['Subject'] = config['sujet']
    msg['From'] = SENDER_EMAIL
    msg['To'] = destinataire

    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)

    corps_personnalise = config['texte_html'].replace("{prenom}", prenom)

    # HTML compatible Outlook (bannière avec couleur de fond pour logo blanc/transparent)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="margin:0; padding:0; background-color:#ffffff; font-family: Arial, sans-serif; color: #333333;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed;">
            <tr>
                <td align="center" style="padding: 10px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="600" style="width: 600px; border: 1px solid #e0e0e0; background-color: #ffffff;">
                        <!-- Bannière d'en-tête avec fond sombre pour faire ressortir le logo -->
                        <tr>
                            <td align="right" valign="top" bgcolor="#1a2b4c" style="background-color: #1a2b4c; padding: 15px;">
                                <img src="cid:logo_asso" alt="Logo" width="120" height="auto" border="0" style="display: block; width: 120px; height: auto; outline: none; text-decoration: none;">
                            </td>
                        </tr>
                        <!-- Contenu du message -->
                        <tr>
                            <td valign="top" style="padding: 25px; font-size: 15px; line-height: 1.6; color: #333333;">
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

    msg_alternative.attach(MIMEText(html_content, "html"))

    # Récupération et intégration du logo via CID (fichier local prioritaire)
    img_data = None
    
    # 1. Essai avec le fichier local 'logo.png' dans le dépôt
    if os.path.exists("logo.png"):
        try:
            with open("logo.png", "rb") as f:
                img_data = f.read()
            print("Logo local 'logo.png' trouvé et chargé.")
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier local 'logo.png' : {e}")

    # 2. Secours : Téléchargement via URL si le fichier local n'existe pas
    if img_data is None:
        try:
            url_logo = config.get('url_logo', '')
            if "github.com" in url_logo and "/blob/" in url_logo:
                url_logo = url_logo.replace("/blob/", "/raw/")
            
            req = urllib.request.Request(url_logo, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                img_data = response.read()
            print("Logo téléchargé depuis l'URL externe.")
        except Exception as e:
            print(f"Avertissement : impossible de télécharger le logo depuis l'URL ({e})")

    # Attachement de l'image si elle a été récupérée
    if img_data:
        try:
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<logo_asso>')
            img.add_header('Content-Disposition', 'inline', filename="logo.png")
            msg.attach(img)
            print("Logo attaché avec succès au message.")
        except Exception as e:
            print(f"Erreur lors de la création de l'image MIME : {e}")

    # Envoi de l'e-mail via le serveur SMTP
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
