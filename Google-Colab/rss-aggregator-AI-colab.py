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
import warnings
from transformers import pipeline, AutoTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ignore specific warnings
warnings.filterwarnings("ignore", message="The secret `HF_TOKEN` does not exist in your Colab secrets.")
warnings.filterwarnings("ignore", category=FutureWarning, message="tokenization_spaces` was not set.*")

# Configure logging with rotation
log_handler = RotatingFileHandler('rss_aggregator.log', maxBytes=1000000, backupCount=5)
logging.basicConfig(
    handlers=[log_handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize zero-shot classification model with explicit tokenizer
model_name = "facebook/bart-large-mnli"
tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
classifier = pipeline("zero-shot-classification", model=model_name, tokenizer=tokenizer)

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
                "topics": ["Artificial Intelligence", "Web Design", "UX/UI", "Programming", "Wordpress", "cyber security"],
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

# Dictionary to track feed status
feed_status = {feed: True for feed in rss_feeds}

def parse_rss(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        channel = root.find('channel')
        if channel is None:
            return []
        
        items = channel.findall('item')
        news = []
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''
            description = item.find('description').text if item.find('description') is not None else ''
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
            
            news.append({
                'title': title,
                'link': link,
                'description': description,
                'published': pub_date
            })
        
        return news
    except RequestException as e:
        logging.error(f"Error retrieving RSS feed from {url}: {str(e)}")
        return []

def apply_ai_filters(news_item):
    # Combine title and description for analysis
    content = f"{news_item['title']} {news_item['description']}"
    
    # Classify content against defined topics
    result = classifier(content, ai_filters['topics'], multi_label=False)
    
    # Check if the most probable topic exceeds the similarity threshold
    if result['scores'][0] > ai_filters['similarity_threshold']:
        logging.info(f"News accepted: {news_item['title']} (Topic: {result['labels'][0]}, Score: {result['scores'][0]})")
        return True
    else:
        logging.info(f"News rejected: {news_item['title']} (Closest topic: {result['labels'][0]}, Score: {result['scores'][0]})")
        return False

def check_connection(url):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except RequestException:
        return False

def extract_first_paragraph(html):
    # Remove HTML tags and take the first paragraph
    clean_text = re.sub('<[^<]+?>', '', html)
    paragraphs = clean_text.split('\n')
    return paragraphs[0] if paragraphs else ''

def check_news():
    for feed in rss_feeds:
        if check_connection(feed):
            if not feed_status[feed]:
                logging.info(f"The source {feed} is back online.")
                feed_status[feed] = True
            
            try:
                news_items = parse_rss(feed)
                for news_item in news_items:
                    if apply_ai_filters(news_item):
                        title = news_item['title']
                        link = news_item['link']
                        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        description = extract_first_paragraph(news_item['description'])
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

    for news_item in news_items:
        item = ET.SubElement(root, "item")
        ET.SubElement(item, "title").text = news_item[0]
        ET.SubElement(item, "link").text = news_item[1]
        ET.SubElement(item, "date").text = news_item[2]
        ET.SubElement(item, "description").text = news_item[3]

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
    global conn, c
    conn = sqlite3.connect('news.db')
    c = conn.cursor()

    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (title TEXT, link TEXT, date TEXT, description TEXT)''')

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

#ERROR:root:Error retrieving RSS feed from https://uxdesign.cc/feed: 429 Client Error: Too Many Requests for url: https://uxdesign.cc/feed
