# RSS Aggregator with AI Filtering

This Python script is an advanced RSS feed aggregator that uses AI-powered filtering to collect and organize news from various sources. It's designed to automate the process of gathering relevant information from multiple RSS feeds while ensuring the content aligns with specified topics of interest.

## Key Features

- **AI-Powered Content Filtering**: Utilizes a zero-shot classification model to categorize and filter news based on predefined topics.
- **Dynamic RSS Feed Management**: Supports adding or removing RSS feeds through a configuration file without needing to restart the script.
- **Automated XML Generation**: Creates an XML file containing recent news items, making it easy to integrate with other systems or websites.
- **Data Retention Policy**: Implements an automatic cleanup of old news items to manage database size.
- **Disk Space Monitoring**: Checks available disk space and logs warnings if it runs low.
- **Robust Error Handling and Logging**: Implements comprehensive logging and error handling for better maintainability and debugging.

## How It Works

1. The script loads configuration from a JSON file, including RSS feed URLs and AI filter settings.
2. It periodically checks each RSS feed for new content.
3. New articles are processed using a zero-shot classification model to determine their relevance to specified topics.
4. Relevant articles are stored in a SQLite database and included in an XML output file.
5. The script runs continuously, performing checks at regular intervals and adapting to configuration changes on the fly.

## Technologies Used

- Python 3
- SQLite for data storage
- `feedparser` for RSS feed parsing
- `transformers` library for AI-powered text classification
- `xml.etree.ElementTree` for XML generation

## Usage

1. Configure your RSS feeds and AI filter settings in `config.json`:

```json
{
  "rss_feeds": [
    "https://www.example.com/feed/",
    "https://www.anothersite.com/rss/"
  ],
  "ai_filters": {
    "topics": ["Artificial Intelligence", "Web Design", "UX/UI", "Programming"],
    "similarity_threshold": 0.5
  }
}
```

2. Run the script:

```bash
python rss_aggregator.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

This project demonstrates the integration of AI technologies with traditional RSS aggregation, providing a smart solution for content curation and information management.
