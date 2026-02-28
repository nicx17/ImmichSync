# Immich Folder Sync Script

A Python script to intelligently automate syncing a local folder of images (like screenshots) to your Immich server. It safely handles both local network connections and external connections, preventing duplicates and automatically organizing uploaded assets into a designated album.

## Features and Working Mechanism

This script operates in the following sequence during a given run:
1. Environment Loading: It securely loads credentials and configuration variables, including your API key, target folder, and Immich URLs.
2. Network Detection: It pings your local network URL first. If that times out, it seamlessly falls back to your external URL. This is ideal for laptops that frequently switch between home Wi-Fi and outside networks.
3. Album Resolution: It queries the Immich API to find the internal ID associated with the album name specified in your configuration.
4. Local Deduplication: It consults a local history file (`immich_upload_history.json`) to skip files that have already been uploaded previously by the script in past runs.
5. Server Deduplication and Uploading: It uploads new files along with critical metadata (creation time, modification time). The script properly interprets Immich's API responses to distinguish between a fully new file being created, a soft duplicate that Immich merged, and a hard conflict.
6. Album Linking: Any successfully finalized uploads are subsequently linked to the specified target album.
7. Status Logging: Every operation is logged both to the console and to a local `immich_backup.log` file, ensuring complete visibility of its operations over time.

## Security Considerations

* Authentication: The script authenticates exclusively via the Immich API Key. The key is loaded from a `.env` file that should be excluded from version control to prevent token leakage.
* Safe Uploads: It uses a purely additive approach. The script reads files from your local system and posts them to the Immich server; it never deletes or modifies your local files.
* Local Storage: Upload history is saved locally within a JSON file to prevent re-upload attempts, ensuring API rate limits and server resources are respected.

## Installation

1. Clone this repository or download the script files to your local machine.
2. Ensure you have Python 3 installed.
3. It is recommended to use a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
4. Install the required dependencies:
   ```bash
   pip install requests python-dotenv
   ```
5. Create a `.env` file in the same directory as the script based on this structure:
   ```env
   SCREENSHOTS_PATH="/path/to/your/folder"
   IMMICH_API_KEY="your_api_key_here"
   IMMICH_LOCAL_URL="http://192.168.x.x:2283"
   IMMICH_EXTERNAL_URL="https://immich.yourdomain.com"
   IMMICH_ALBUM_NAME="Your Target Album"
   ```

## Running the Script

Once configured, run the script via Python:

```bash
python uploader_v1.py
```

For continuous backups, you can schedule this script to run periodically using a cron job (Linux/macOS) or Task Scheduler (Windows).
