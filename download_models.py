#!/usr/bin/env python3
import os
import json
import requests
import subprocess
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_file(url, output_path):
    """Download a file using aria2c"""
    cmd = [
        'aria2c',
        '--console-log-level=error',
        '-c',  # Continue downloading if partial file exists
        '-x', '8',  # Use 8 connections
        '-s', '8',  # Split file into 8 parts
        '-k', '1M',  # Minimum split size
        url,
        '-d', str(output_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def get_config(config_url):
    """Fetch configuration from URL"""
    try:
        response = requests.get(config_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch config from {config_url}: {e}")
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
        'input',
        'output'
    ]
    
    for dir_path in directories:
        full_path = base_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {full_path}")

def main():
    # Environment variables
    config_url = os.getenv('MODELS_CONFIG_URL', 'https://raw.githubusercontent.com/poomshift/comfyui-docker-new/refs/heads/main/models_config.json')
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
    config = get_config(config_url)
    if not config:
        logger.error("Failed to get configuration, exiting.")
        return
    
    # Download models
    for category, urls in config.items():
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