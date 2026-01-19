import os
import requests
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
# ================= CONFIGURATION =================
SCREENSHOTS_FOLDER = os.getenv("SCREENSHOTS_PATH")
API_KEY = os.getenv("IMMICH_API_KEY")
LOCAL_URL = os.getenv("IMMICH_LOCAL_URL")
EXTERNAL_URL = os.getenv("IMMICH_EXTERNAL_URL")
ALBUM_NAME = os.getenv("IMMICH_ALBUM_NAME")
# Files are saved in the same directory as the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(SCRIPT_DIR, "immich_upload_history.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "immich_backup.log")
DEVICE_ID = "Arch-Uploader"

# ================= LOGGING SETUP =================
# This sets up the log file with timestamps
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# This ensures logs ALSO print to the console (Terminal)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
# =================================================

def get_active_url():
    if not LOCAL_URL: return None
    logging.info(f"Checking connection to: {LOCAL_URL}")
    try:
        response = requests.get(f"{LOCAL_URL}/api/server/ping", timeout=2)
        if response.status_code == 200:
            logging.info("Local network detected.")
            return LOCAL_URL
    except requests.RequestException:
        pass
    
    if EXTERNAL_URL:
        logging.info("Switching to External URL.")
        return EXTERNAL_URL
    return None

def get_album_id(base_url, api_key, name):
    url = f"{base_url}/api/albums"
    headers = {'x-api-key': api_key, 'Accept': 'application/json'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        albums = response.json()
        for album in albums:
            if album['albumName'] == name:
                return album['id']
        return None
    except Exception as e:
        logging.error(f"Error fetching albums: {e}")
        return None

def add_to_album(base_url, api_key, album_id, asset_id):
    url = f"{base_url}/api/albums/{album_id}/assets"
    headers = {
        'x-api-key': api_key, 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    payload = json.dumps({"ids": [asset_id]})
    
    try:
        response = requests.put(url, headers=headers, data=payload)
        response.raise_for_status()
        logging.info(f"   -- Added to album '{ALBUM_NAME}'")
        return True
    except Exception as e:
        logging.error(f"   -- Failed to add to album: {e}")
        return False

def upload_asset(file_path, base_url, api_key):
    url = f"{base_url}/api/assets"
    if not os.path.isfile(file_path): return None

    stats = os.stat(file_path)
    files = {'assetData': open(file_path, 'rb')}
    
    device_asset_id = f"{os.path.basename(file_path)}-{stats.st_size}"
    
    data = {
        'deviceAssetId': device_asset_id,
        'deviceId': DEVICE_ID,
        'fileCreatedAt': datetime.fromtimestamp(stats.st_ctime).isoformat(),
        'fileModifiedAt': datetime.fromtimestamp(stats.st_mtime).isoformat(),
        'isFavorite': 'false',
    }
    
    headers = {'x-api-key': api_key, 'Accept': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=data, files=files)
        response.raise_for_status()
        return response.json().get('id')
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            logging.warning(f"Duplicate on server: {os.path.basename(file_path)}")
            try:
                return e.response.json().get('id')
            except:
                return "DUPLICATE_UNKNOWN_ID"
        logging.error(f"Upload failed: {e}")
        return None
    finally:
        files['assetData'].close()

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f: return set(json.load(f))
        except: return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, 'w') as f: json.dump(list(history_set), f, indent=4)

def main():
    # 1. Validation
    if not SCREENSHOTS_FOLDER or not os.path.exists(SCREENSHOTS_FOLDER):
        logging.error("Screenshots folder not found.")
        return
    if not ALBUM_NAME:
        logging.error("IMMICH_ALBUM_NAME not set in .env")
        return

    # 2. Connection
    base_url = get_active_url()
    if not base_url: 
        logging.error("Could not connect to any Immich instance.")
        return

    logging.info(f"Looking for album: '{ALBUM_NAME}'")
    target_album_id = get_album_id(base_url, API_KEY, ALBUM_NAME)
    
    if not target_album_id:
        logging.error(f"Album '{ALBUM_NAME}' not found on server! Exiting.")
        return

    # 3. Processing
    uploaded_history = load_history()
    supported_exts = ('.png', '.jpg', '.jpeg', '.webp')
    
    files_to_check = [
        os.path.join(SCREENSHOTS_FOLDER, f) 
        for f in os.listdir(SCREENSHOTS_FOLDER) 
        if f.lower().endswith(supported_exts)
    ]
    files_to_check.sort(key=os.path.getmtime)

    count = 0
    for file_path in files_to_check:
        filename = os.path.basename(file_path)
        
        if filename in uploaded_history:
            continue
            
        logging.info(f"Uploading: {filename}")
        asset_id = upload_asset(file_path, base_url, API_KEY)
        
        if asset_id:
            if asset_id != "DUPLICATE_UNKNOWN_ID":
                add_to_album(base_url, API_KEY, target_album_id, asset_id)
            
            uploaded_history.add(filename)
            save_history(uploaded_history)
            count += 1

    if count > 0:
        logging.info(f"Done! Processed {count} images.")
    else:
        # Optional: Uncomment if you want logs even when nothing happens
        # logging.info("No new screenshots found.")
        pass

if __name__ == "__main__":
    main()