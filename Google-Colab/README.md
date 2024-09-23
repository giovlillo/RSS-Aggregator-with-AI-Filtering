# RSS Aggregator with AI Filtering (Google Colab edition)

This project is an AI-powered RSS feed aggregator designed to run on Google Colab. It fetches news from various RSS feeds, applies AI-based filtering, and stores relevant articles in a SQLite database.

## Features

- Fetches news from multiple RSS feeds
- Uses AI to filter news based on predefined topics
- Stores filtered news in a SQLite database
- Generates an XML file with recent news
- Implements a retention policy to manage database size
- Monitors disk space
- Configurable via a JSON file

## Prerequisites

To run this script on Google Colab, you'll need:

1. A Google account to access Google Colab
2. Basic knowledge of Python and Google Colab

## Setup

1. Create a new notebook in Google Colab.
2. Copy the entire script into a code cell in your Colab notebook.
3. Create a new code cell and add the following to install required libraries:

   ```python
   !pip install transformers sklearn
   ```

4. Upload the `config.json` file to your Colab environment or create it using the provided default configuration.

## Usage

1. Run the cell with the library installation commands.
2. Run the cell containing the main script.
3. The script will start running, checking for news every hour.

## Configuration

You can modify the `config.json` file to customize the RSS feeds and AI filtering parameters. The configuration includes:

- `rss_feeds`: List of RSS feed URLs
- `ai_filters`:
  - `topics`: List of topics for classification
  - `similarity_threshold`: Threshold for accepting a news item

## Output

- `recent_news.xml`: Contains the most recent news items
- `rss_aggregator.log`: Log file with information about the script's operation
- `news.db`: SQLite database storing the filtered news items

## Notes

- This script is adapted to run on Google Colab, which means it will stop running when your Colab session ends. For continuous operation, consider deploying it on a persistent server.
- The script uses a pre-trained model from Hugging Face for zero-shot classification. Ensure you have a stable internet connection for the initial model download.
- Be mindful of Colab's usage limits and the terms of service of the RSS feeds you're aggregating.

## Contributing

Feel free to fork this project and submit pull requests with improvements or bug fixes.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
