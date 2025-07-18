import os
import json
import asyncio
import aiohttp
from pathlib import Path
import logging
import sys
from typing import List, Dict, Any

# Prevent duplicate logging
logging.getLogger().handlers = []

# Set up logging to file only, since stdout is already captured by tee in start.sh
log_file_path = "/workspace/logs/forge.log"
file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(message)s")
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Also log to stdout for visibility
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(
    logging.Formatter("%(message)s")
)
logger.addHandler(stdout_handler)

# Global semaphore to limit concurrent downloads
download_semaphore = asyncio.Semaphore(3)

# Model category to Forge folder mapping
CATEGORY_TO_PATH = {
    "Stable-diffusion": "models/Stable-diffusion",
    "VAE": "models/VAE",
    "Lora": "models/Lora",
    "ESRGAN": "models/ESRGAN",
    "ControlNet": "models/ControlNet",
    "text_encoder": "models/text_encoder",
}

async def download_file(
    url: str, output_path: Path, semaphore: asyncio.Semaphore
) -> bool:
    """Download a file using aria2c with optimized settings for faster downloads (async)"""
    async with semaphore:
        filename = url.split("/")[-1]
        logger.info(f"Starting download of {filename} from {url}")

        cmd = [
            "aria2c",
            "--console-log-level=warn",  # Reduce verbosity to warnings only
            "-c",  # Continue downloading if partial file exists
            "-x",
            "4",  # Increase concurrent connections to 4
            "-s",
            "4",  # Split file into 4 parts
            "-k",
            "1M",  # Minimum split size
            "--file-allocation=none",  # Disable file allocation for faster start
            "--optimize-concurrent-downloads=true",  # Optimize concurrent downloads
            "--max-connection-per-server=16",  # Maximum connections per server
            "--min-split-size=1M",  # Minimum split size
            "--max-tries=5",  # Maximum retries
            "--retry-wait=10",  # Wait between retries
            "--connect-timeout=30",  # Connection timeout
            "--timeout=600",  # Timeout for stalled downloads
            "--summary-interval=30",  # Show summary every 30 seconds
            url,
            "-d",
            str(output_path),
            "-o",
            filename,  # Specify output filename
        ]

        try:
            logger.info(f"Running download command for {filename}")
            # Use async subprocess for non-blocking execution
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Successfully downloaded {filename}")
                return True
            else:
                error_msg = stderr.decode("utf-8") if stderr else stdout.decode()
                logger.error(f"Failed to download {filename}: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error while downloading {url}: {e}")
            return False


async def get_config_async(config_path: str) -> Dict[str, Any]:
    """Load configuration from file or URL (async)"""
    try:
        # Check if it's a URL
        if config_path.startswith(("http://", "https://")):
            async with aiohttp.ClientSession() as session:
                async with session.get(config_path) as response:
                    response.raise_for_status()
                    # Get text content and parse as JSON manually to handle GitHub's text/plain mimetype
                    text_content = await response.text()
                    return json.loads(text_content)
        else:
            # Load from local file
            with open(config_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return None


# Only create Forge-relevant directories
def ensure_directories(base_path: Path) -> None:
    directories = [
        "models/Stable-diffusion",
        "models/VAE",
        "models/Lora",
        "models/ESRGAN",
        "models/ControlNet",
        "models/text_encoder",
        "outputs",
    ]
    for dir_path in directories:
        full_path = base_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {full_path}")


async def download_category_models(
    category: str, urls: List[str], base_path: Path, force_download: bool = False
):
    """Download all models in a category concurrently"""
    if not isinstance(urls, list):
        logger.warning(f"Skipping '{category}' as it's not a list of URLs")
        return []

    # Map category to Forge folder
    if category not in CATEGORY_TO_PATH:
        logger.warning(f"Unknown category '{category}', skipping.")
        return []
    category_path = base_path / CATEGORY_TO_PATH[category]
    category_path.mkdir(parents=True, exist_ok=True)

    # Prepare download tasks
    download_tasks = []
    for url in urls:
        filename = url.split("/")[-1]
        if (category_path / filename).exists() and not force_download:
            logger.info(f"Skipping {filename}, file already exists")
            continue
        logger.info(f"Queuing download: {filename} to {category_path}")
        task = download_file(url, category_path, download_semaphore)
        download_tasks.append((task, filename))
    if not download_tasks:
        logger.info(f"No new models to download in category: {category}")
        return []
    logger.info(
        f"Starting {len(download_tasks)} concurrent downloads for category: {category}"
    )
    tasks = []
    for i, (task, filename) in enumerate(download_tasks):
        t = asyncio.create_task(
            track_download_progress(
                task, filename, i + 1, len(download_tasks), category
            )
        )
        tasks.append(t)
    return tasks


async def track_download_progress(
    task: asyncio.Task, filename: str, current: int, total: int, category: str
) -> bool:
    """Track download progress and log results"""
    try:
        result = await task
        if result:
            logger.info(
                f"✓ [{current}/{total}] Successfully downloaded {filename} ({category})"
            )
        else:
            logger.error(
                f"✗ [{current}/{total}] Failed to download {filename} ({category})"
            )
        return result
    except Exception as e:
        logger.error(
            f"✗ [{current}/{total}] Error downloading {filename} ({category}): {e}"
        )
        return False


async def main():
    """Main async function to download models concurrently"""
    config_path = os.getenv("MODELS_CONFIG_URL", "/workspace/models_config.json")
    skip_download = os.getenv("SKIP_MODEL_DOWNLOAD", "").lower() == "true"
    force_download = os.getenv("FORCE_MODEL_DOWNLOAD", "").lower() == "true"
    if skip_download:
        logger.info("Model download skipped due to SKIP_MODEL_DOWNLOAD=true")
        return
    # Use Forge path
    forge_path = "/workspace/stable-diffusion-webui-forge"
    base_path = Path(forge_path)
    ensure_directories(base_path)
    # Check if config path is a URL or local file
    if config_path.startswith(("http://", "https://")):
        logger.info(f"Using models_config.json from URL: {config_path}")
    else:
        local_config_path = Path(config_path)
        if local_config_path.exists():
            logger.info(f"Using local models_config.json: {config_path}")
            config_path = str(local_config_path.absolute())
        else:
            logger.error(f"Local config file not found at {config_path}")
            default_config = {
                "Stable-diffusion": [],
                "VAE": [],
                "Lora": [],
                "ESRGAN": [],
                "ControlNet": [],
                "text_encoder": [],
            }
            logger.info("Using default empty configuration")
            with open("/workspace/models_config.json", "w") as f:
                json.dump(default_config, f, indent=4)
            config_path = "/workspace/models_config.json"
    config = await get_config_async(config_path)
    if not config:
        logger.error("Failed to get configuration, exiting.")
        return
    total_models = sum(len(urls) for urls in config.values() if isinstance(urls, list))
    logger.info(f"Found {total_models} models in configuration")
    logger.info(f"Maximum concurrent downloads: 5")
    category_tasks = []
    for category, urls in config.items():
        if isinstance(urls, list) and urls:
            tasks = await download_category_models(category, urls, base_path, force_download)
            [category_tasks.append(task) for task in tasks]
    if category_tasks:
        logger.info(
            f"Starting concurrent downloads for {len(category_tasks)} categories..."
        )
        await asyncio.gather(*category_tasks)
        logger.info("All model downloads completed!")
    else:
        logger.info("No models to download.")


if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Download process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
