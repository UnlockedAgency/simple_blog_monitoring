import requests
from bs4 import BeautifulSoup
import sqlite3
import smtplib
from email.mime.text import MIMEText
import schedule
import time
import config

DB_PATH = 'monitor.db'
URL_FILE = 'urls.txt'

def setup_database():
    """Set up the SQLite database and create the posts table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the 'posts' table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            url TEXT PRIMARY KEY,
            last_known_post TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def fetch_latest_post(url):
    """Fetch the latest post from the given URL."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the latest article using the H2 tag with a class
    latest_post = soup.find('h2', class_='add_your_class_here')
    
    if latest_post:
        title = latest_post.get_text(strip=True)
        post_url = latest_post.find_parent('a')['href']  # Assuming the H2 is within an anchor tag
        return title, post_url
    return None, None

def check_for_new_posts():
    """Check each URL for new posts and send an alert if found."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(URL_FILE, 'r') as file:
        urls = file.readlines()
    
    for url in urls:
        url = url.strip()
        title, post_url = fetch_latest_post(url)
        
        if title and post_url:
            cursor.execute("SELECT last_known_post FROM posts WHERE url = ?", (url,))
            row = cursor.fetchone()
            
            if row is None or row[0] != post_url:
                send_email_alert(url, title, post_url)
                cursor.execute("REPLACE INTO posts (url, last_known_post) VALUES (?, ?)", (url, post_url))
    
    conn.commit()
    conn.close()

def send_email_alert(url, title, post_url):
    """Send an email alert for a new post."""
    msg = MIMEText(f"New post detected at {url}\n\nTitle: {title}\nLink: {post_url}")
    msg['Subject'] = "New Post Alert!"
    msg['From'] = config.EMAIL_FROM
    msg['To'] = config.EMAIL_TO
    
    with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
        server.starttls()  # Upgrade the connection to secure
        server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        server.send_message(msg)


if __name__ == "__main__":
    setup_database()  # Initialize the database

    check_for_new_posts()  # Run the check immediately for testing

    schedule.every().day.at("09:00").do(check_for_new_posts)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
