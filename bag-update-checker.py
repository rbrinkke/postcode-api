#!/usr/bin/env python3
"""
BAG Update Checker - Checks for new BAG versions and downloads them
Based on update-strategy.json implementation plan
"""

import json
import logging
import os
import sys
import subprocess
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import time
import shutil

# Configuration
BASE_DIR = Path("/opt/postcode")
BAGCONV_DIR = BASE_DIR / "bagconv-source"
DOWNLOAD_VERSION_FILE = BASE_DIR / "download-bag-version.json"
CURRENT_VERSION_FILE = BASE_DIR / "current-bag-version.json"
PDOK_FEED_URL = "https://service.pdok.nl/lv/bag/atom/bag.xml"
BAGCONV_REPO = "https://github.com/berthubert/bagconv.git"
ZIP_FILENAME = "lvbag-extract-nl.zip"
REQUIRED_SPACE_GB = 7  # GB needed for download + extraction

# Setup logging
LOG_FILE = '/var/log/bag-update.log'

# Try to create log file if it doesn't exist
try:
    Path(LOG_FILE).touch(exist_ok=True)
    handlers = [
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
except PermissionError:
    # If we can't write to /var/log, use local directory
    LOG_FILE = BASE_DIR / 'bag-update.log'
    handlers = [
        logging.FileHandler(str(LOG_FILE)),
        logging.StreamHandler()
    ]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger('bag-update-checker')


def get_disk_free_gb(path):
    """Get free disk space in GB for the given path"""
    stat = shutil.disk_usage(path)
    return stat.free / (1024 ** 3)


def fetch_pdok_version():
    """Fetch the current version from PDOK ATOM feed"""
    logger.info(f"Fetching PDOK feed from {PDOK_FEED_URL}")
    try:
        with urllib.request.urlopen(PDOK_FEED_URL, timeout=30) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        # Get the updated timestamp
        updated_elem = root.find('atom:updated', ns)
        if updated_elem is None:
            raise ValueError("Could not find updated timestamp in feed")
        
        version_date = updated_elem.text
        
        # Find the ZIP download entry
        entries = root.findall('atom:entry', ns)
        zip_info = None
        
        for entry in entries:
            title_elem = entry.find('atom:title', ns)
            if title_elem is not None and "Zip archief" in title_elem.text:
                link_elem = entry.find('.//atom:link[@rel="alternate"]', ns)
                if link_elem is not None:
                    zip_info = {
                        "title": title_elem.text,
                        "url": link_elem.get('href'),
                        "size": int(link_elem.get('length', 0)),
                        "type": link_elem.get('type')
                    }
                    break
        
        if not zip_info:
            raise ValueError("Could not find ZIP download in feed")
        
        return {
            "version_date": version_date,
            "downloads": {
                zip_info["title"]: {
                    "url": zip_info["url"],
                    "size": zip_info["size"],
                    "type": zip_info["type"]
                }
            },
            "checked_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error fetching PDOK feed: {e}")
        raise


def load_version_file(filepath):
    """Load version information from JSON file"""
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


def save_version_file(filepath, data):
    """Save version information to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved version info to {filepath}")


def update_bagconv():
    """Update or clone the bagconv repository"""
    logger.info("Updating bagconv repository")
    
    if not BAGCONV_DIR.exists():
        BAGCONV_DIR.mkdir(parents=True, exist_ok=True)
    
    git_dir = BAGCONV_DIR / ".git"
    
    try:
        if git_dir.exists():
            # Repository exists, do a pull
            logger.info("Pulling latest bagconv changes")
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=BAGCONV_DIR,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Git pull output: {result.stdout}")
        else:
            # Clone the repository
            logger.info("Cloning bagconv repository")
            result = subprocess.run(
                ["git", "clone", BAGCONV_REPO, "."],
                cwd=BAGCONV_DIR,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Repository cloned successfully")
        
        # Get current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=BAGCONV_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        commit_hash = result.stdout.strip()
        logger.info(f"Bagconv at commit: {commit_hash}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e.stderr}")
        return False


def download_with_progress(url, filepath, expected_size):
    """Download file with progress reporting and resume support"""
    headers = {}
    mode = 'wb'
    resume_pos = 0
    
    # Check if partial file exists
    if filepath.exists():
        resume_pos = filepath.stat().st_size
        if resume_pos < expected_size:
            logger.info(f"Resuming download from {resume_pos} bytes")
            headers['Range'] = f'bytes={resume_pos}-'
            mode = 'ab'
        elif resume_pos == expected_size:
            logger.info("File already fully downloaded")
            return True
        else:
            logger.warning("Existing file larger than expected, starting fresh")
            filepath.unlink()
            resume_pos = 0
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = expected_size
            downloaded = resume_pos
            
            logger.info(f"Downloading {total_size / (1024**3):.1f} GB")
            
            with open(filepath, mode) as f:
                while True:
                    chunk = response.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress reporting every 100MB
                    if downloaded % (100 * 1024 * 1024) < (1024 * 1024):
                        progress = (downloaded / total_size) * 100
                        logger.info(f"Progress: {progress:.1f}% ({downloaded / (1024**3):.1f} GB)")
            
            # Verify final size
            final_size = filepath.stat().st_size
            if final_size == expected_size:
                logger.info("Download completed successfully")
                return True
            else:
                logger.error(f"Size mismatch: expected {expected_size}, got {final_size}")
                return False
                
    except Exception as e:
        logger.error(f"Download error: {e}")
        return False


def main():
    """Main update check logic"""
    logger.info("=== BAG Update Checker Started ===")
    
    try:
        # Step 1: Check for new version
        logger.info("Step 1: Checking for new version")
        pdok_version = fetch_pdok_version()
        download_version = load_version_file(DOWNLOAD_VERSION_FILE)
        
        new_version_available = False
        if download_version:
            if pdok_version['version_date'] > download_version['version_date']:
                new_version_available = True
                logger.info(f"New version available: {pdok_version['version_date']}")
            else:
                logger.info(f"No new version. Current: {download_version['version_date']}")
        else:
            logger.info("No download version found, treating as new")
            new_version_available = True
        
        # Step 2: Update bagconv
        logger.info("Step 2: Preparing bagconv")
        if not update_bagconv():
            logger.warning("Failed to update bagconv, continuing anyway")
        
        # Step 3: Download if needed
        if new_version_available:
            logger.info("Step 3: Downloading new BAG data")
            
            # Check disk space
            free_gb = get_disk_free_gb(BAGCONV_DIR)
            if free_gb < REQUIRED_SPACE_GB:
                logger.error(f"Insufficient disk space: {free_gb:.1f} GB free, need {REQUIRED_SPACE_GB} GB")
                sys.exit(1)
            
            # Get download info
            zip_title = list(pdok_version['downloads'].keys())[0]
            zip_info = pdok_version['downloads'][zip_title]
            zip_path = BAGCONV_DIR / ZIP_FILENAME
            
            # Download the file
            if download_with_progress(zip_info['url'], zip_path, zip_info['size']):
                # Update download version file
                save_version_file(DOWNLOAD_VERSION_FILE, pdok_version)
                logger.info("Download completed and version updated")
            else:
                logger.error("Download failed")
                sys.exit(1)
        else:
            logger.info("Step 3: No download needed, already have latest version")
        
        logger.info("=== BAG Update Checker Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()