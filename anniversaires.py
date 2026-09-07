import os
import json
import datetime
import smtplib
import requests
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
    
    # Paheko renvoie parfois les résultats dans une clé "results"
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data

def envoyer_email(destinataire, prenom):
    """Envoie le mail au format HTML avec le logo en haut à droite."""
    msg = MIMEMultipart("alternative")
    msg['Subject'] = config['sujet']
    msg['From'] = SENDER_EMAIL
    msg['To'] = destinataire

    corps_personnalise = config['texte_html'].replace("{prenom}", prenom)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; padding: 20px;">
            <tr>
                <td style="vertical-align: top;">
                    {corps_personnalise}
                </td>
                <td style="vertical-align: top; text-align: right; width: 120px;">
                    <img src="{config['url_logo']}" alt="Logo" style="max-width: 100px; height: auto;">
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_content, "html"))

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
        # S'assure que 'm' est bien un dictionnaire d'informations
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
