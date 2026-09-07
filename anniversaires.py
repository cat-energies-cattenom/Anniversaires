import os
import json
import datetime
import smtplib
import requests
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# 1. Chargement de la configuration
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 2. Variables d'environnement GitHub Secrets
PAHEKO_URL = os.environ['PAHEKO_URL'].rstrip('/')
PAHEKO_USER = os.environ['PAHEKO_USER']
PAHEKO_PASSWORD = os.environ['PAHEKO_PASSWORD']

SMTP_SERVER = os.environ['SMTP_SERVER']
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ['SMTP_USER']
SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', SMTP_USER)

today_str = datetime.date.today().strftime("%m-%d")

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
    return data.get("results", data) if isinstance(data, dict) else data

def envoyer_email(destinataire, prenom):
    """Envoie l'email en injectant les variables dans template.html."""
    msg_root = MIMEMultipart('related')
    msg_root['Subject'] = config['sujet']
    msg_root['From'] = SENDER_EMAIL
    msg_root['To'] = destinataire

    msg_alternative = MIMEMultipart('alternative')
    msg_root.attach(msg_alternative)

    # 1. Préparation du texte HTML
    corps_personnalise = config['texte_html'].replace("{prenom}", prenom)

    # 2. Lecture et remplissage du fichier template.html
    try:
        with open('template.html', 'r', encoding='utf-8') as f:
            template = f.read()
        html_content = template.replace("{corps_personnalise}", corps_personnalise)
    except Exception as e:
        print(f"Erreur lors de la lecture de template.html : {e}")
        return

    msg_alternative.attach(MIMEText(html_content, 'html', 'utf-8'))

    # 3. Chargement de l'image (local ou distant)
    img_data = None
    if os.path.exists("logo.png"):
        try:
            with open("logo.png", "rb") as f:
                img_data = f.read()
        except Exception as e:
            print(f"Erreur lecture logo local : {e}")

    if img_data is None:
        try:
            url_logo = config.get('url_logo', '')
            if "github.com" in url_logo and "/blob/" in url_logo:
                url_logo = url_logo.replace("/blob/", "/raw/")
            req = urllib.request.Request(url_logo, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                img_data = response.read()
        except Exception as e:
            print(f"Erreur chargement logo distant : {e}")

    # 4. Attachement de l'image via CID (logo_asso)
    if img_data:
        try:
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<logo_asso>')
            img.add_header('Content-Disposition', 'inline', filename="logo.png")
            msg_root.attach(img)
        except Exception as e:
            print(f"Erreur attachement CID : {e}")

    # 5. Envoi du mail
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, destinataire, msg_root.as_string())

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
