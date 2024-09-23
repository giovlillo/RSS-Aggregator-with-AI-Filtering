import feedparser
import time
import sqlite3
from datetime import datetime, timedelta
import requests
from requests.exceptions import RequestException
import logging
from logging.handlers import RotatingFileHandler
import xml.etree.ElementTree as ET
import os
import re
import shutil
import json
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging with rotation
log_handler = RotatingFileHandler('rss_aggregator.log', maxBytes=1000000, backupCount=5)
logging.basicConfig(
    handlers=[log_handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize zero-shot classification model
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Function to load configuration
def load_config():
    try:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
        return config
    except FileNotFoundError:
        logging.error("Configuration file not found. Creating a default configuration file.")
        default_config = {
            "rss_feeds": [
                "https://www.webdesignerdepot.com/feed/",
                "https://www.smashingmagazine.com/feed/",
                "https://uxmovement.com/feed/",
                "https://uxdesign.cc/feed"
            ],
            "ai_filters": {
                "topics": ["Artificial Intelligence", "Web Design", "UX/UI", "Programming"],
                "similarity_threshold": 0.5
            }
        }
        with open('config.json', 'w') as config_file:
            json.dump(default_config, config_file, indent=4)
        return default_config
    except json.JSONDecodeError:
        logging.error("Error parsing configuration file. Using default configuration.")
        return {"rss_feeds": [], "ai_filters": {"topics": [], "similarity_threshold": 0.5}}

# Load configuration
config = load_config()
rss_feeds = config['rss_feeds']
ai_filters = config['ai_filters']

def apply_ai_filters(news):
    # Combine title and description for analysis
    content = f"{news.title} {news.description}"
    
    # Classify content against defined topics
    result = classifier(content, ai_filters['topics'])
    
    # Check if the most probable topic exceeds the similarity threshold
    if result['scores'][0] > ai_filters['similarity_threshold']:
        logging.info(f"News accepted: {news.title} (Topic: {result['labels'][0]}, Score: {result['scores'][0]})")
        return True
    else:
        logging.info(f"News rejected: {news.title} (Closest topic: {result['labels'][0]}, Score: {result['scores'][0]})")
        return False

def check_news():
    for feed in rss_feeds:
        if check_connection(feed):
            if not feed_status[feed]:
                logging.info(f"The source {feed} is back online.")
                feed_status[feed] = True
            
            try:
                news_items = feedparser.parse(feed)
                for news in news_items.entries:
                    if apply_ai_filters(news):
                        title = news.title
                        link = news.link
                        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        description = extract_first_paragraph(news.description)
                        # Limit description to 700 characters
                        description = description[:700]

                        c.execute("SELECT * FROM news WHERE title=? AND link=?", (title, link))
                        if c.fetchone() is None:
                            logging.info(f"New news filtered with AI: {title}")
                            c.execute("INSERT INTO news VALUES (?, ?, ?, ?)", (title, link, date, description))
                            conn.commit()
            except Exception as e:
                logging.error(f"Error processing {feed}: {str(e)}")
        else:
            if feed_status[feed]:
                logging.warning(f"Unable to connect to {feed}. Skipping this source.")
                feed_status[feed] = False

def generate_xml():
    root = ET.Element("news")
    two_weeks_ago = (datetime.now() - timedelta(weeks=2)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT * FROM news WHERE date > ? ORDER BY date DESC", (two_weeks_ago,))
    news_items = c.fetchall()

    for news in news_items:
        item = ET.SubElement(root, "item")
        ET.SubElement(item, "title").text = news[0]
        ET.SubElement(item, "link").text = news[1]
        ET.SubElement(item, "date").text = news[2]
        ET.SubElement(item, "description").text = news[3]

    tree = ET.ElementTree(root)
    tree.write("recent_news.xml", encoding="utf-8", xml_declaration=True)
    logging.info("XML file generated successfully: recent_news.xml")

def retention_policy():
    # Delete news older than two months
    two_months_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("DELETE FROM news WHERE date < ?", (two_months_ago,))
    deleted_news = c.rowcount
    conn.commit()
    logging.info(f"Retention policy applied: {deleted_news} news items deleted.")

def check_disk_space():
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)  # Convert bytes to GB
    if free_gb < 1:
        logging.warning(f"Warning: disk space running low. Only {free_gb}GB left.")
    return free_gb

def main():
    while True:
        # Reload configuration at each iteration
        global config, rss_feeds, feed_status
        config = load_config()
        new_feeds = set(config['rss_feeds']) - set(rss_feeds)
        removed_feeds = set(rss_feeds) - set(config['rss_feeds'])
        
        if new_feeds:
            logging.info(f"New feeds added: {new_feeds}")
            for feed in new_feeds:
                feed_status[feed] = True
        
        if removed_feeds:
            logging.info(f"Feeds removed: {removed_feeds}")
            for feed in removed_feeds:
                del feed_status[feed]
        
        rss_feeds = config['rss_feeds']
        
        logging.info("Starting new news check...")
        check_news()
        generate_xml()
        retention_policy()
        free_space = check_disk_space()
        logging.info(f"Check completed. Free disk space: {free_space}GB")
        logging.info("Next check in one hour.")
        time.sleep(3600)  # Wait for an hour

if __name__ == "__main__":
    main()
