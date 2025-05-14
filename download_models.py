#!/usr/bin/env python3
import os
import json
import requests
import subprocess
from pathlib import Path
import logging

# Set up logging to both console and file
log_file_path = '/workspace/logs/comfyui.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def download_file(url, output_path):
    """Download a file using aria2c with optimized settings for faster downloads"""
    filename = url.split('/')[-1]
    logger.info(f"Starting download of {filename} from {url}")
    
    cmd = [
        'aria2c',
        '--console-log-level=info',  # Changed to info to see progress
        '-c',  # Continue downloading if partial file exists
        '-x', '16',  # Increase concurrent connections to 16
        '-s', '16',  # Split file into 16 parts
        '-k', '1M',  # Minimum split size
        '--file-allocation=none',  # Disable file allocation for faster start
        '--optimize-concurrent-downloads=true',  # Optimize concurrent downloads
        '--max-connection-per-server=16',  # Maximum connections per server
        '--min-split-size=1M',  # Minimum split size
        '--max-tries=5',  # Maximum retries
        '--retry-wait=10',  # Wait between retries
        '--connect-timeout=30',  # Connection timeout
        '--timeout=600',  # Timeout for stalled downloads
        '--summary-interval=30',  # Show summary every 30 seconds
        url,
        '-d', str(output_path),
        '-o', filename  # Specify output filename
    ]
    
    try:
        logger.info(f"Command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        
        # Log the download progress
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(line)
        
        process.wait()
        if process.returncode == 0:
            logger.info(f"Successfully downloaded {filename}")
            return True
        else:
            logger.error(f"Failed to download {filename}: Return code {process.returncode}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while downloading {url}: {e}")
        return False

def get_config(config_path):
    """Load configuration from file or URL"""
    try:
        # Check if it's a URL
        if config_path.startswith(('http://', 'https://')):
            response = requests.get(config_path)
            response.raise_for_status()
            return response.json()
        else:
            # Load from local file
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return None

def ensure_directories(base_path):
    """Ensure all required directories exist"""
    directories = [
        'models/checkpoints',
        'models/vae',
        'models/unet',
        'models/diffusion_models',
        'models/text_encoders',
        'models/loras',
        'models/upscale_models',
        'models/clip',
        'models/controlnet',
        'models/clip_vision',
        'models/ipadapter',
        'models/style_models',
        'input',
        'output'
    ]
    
    for dir_path in directories:
        full_path = base_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {full_path}")

def main():
    # Environment variables
    config_path = os.getenv('MODELS_CONFIG_URL', '/workspace/models_config.json')
    skip_download = os.getenv('SKIP_MODEL_DOWNLOAD', '').lower() == 'true'
    force_download = os.getenv('FORCE_MODEL_DOWNLOAD', '').lower() == 'true'
    
    if skip_download:
        logger.info("Model download skipped due to SKIP_MODEL_DOWNLOAD=true")
        return
    
    # Base path for ComfyUI
    base_path = Path('/workspace/ComfyUI')
    
    # Ensure directories exist
    ensure_directories(base_path)
    
    # Fetch configuration
    config = get_config(config_path)
    if not config:
        logger.error("Failed to get configuration, exiting.")
        return
    
    # Download models from each category
    for category, urls in config.items():
        if not isinstance(urls, list):
            logger.warning(f"Skipping '{category}' as it's not a list of URLs")
            continue
            
        category_path = base_path / 'models' / category
        category_path.mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            # Extract filename from URL
            filename = url.split('/')[-1]
            
            # Skip if file exists and force_download is False
            if (category_path / filename).exists() and not force_download:
                logger.info(f"Skipping {filename}, file already exists")
                continue
            
            logger.info(f"Downloading {filename} to {category_path}")
            if download_file(url, category_path):
                logger.info(f"Successfully downloaded {filename}")
            else:
                logger.error(f"Failed to download {filename}")

if __name__ == '__main__':
    main()