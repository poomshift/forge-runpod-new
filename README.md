# ComfyUI Docker

This repository contains a Docker setup for running ComfyUI with Hunyuan video generation capabilities.

## Features

- ComfyUI with pre-installed custom nodes
- Hunyuan video generation support
- Web-based log viewer
- Model downloading system
- GitHub Actions workflow for automatic Docker image building

## Usage

### Running the Docker Image

```bash
docker run -it --gpus all -p 8188:8188 -p 8888:8888 -p 8189:8189 promptalchemist/comfyui-docker-new:latest
```

- Port 8188: ComfyUI interface
- Port 8888: Jupyter Lab
- Port 8189: Log viewer

### Environment Variables

- `UPDATE_ON_START`: Set to "true" to update ComfyUI and nodes on startup (default: false)
- `MODELS_CONFIG_URL`: URL to models configuration JSON (default: from this repository)
- `SKIP_MODEL_DOWNLOAD`: Set to "true" to skip model downloading (default: false)
- `FORCE_MODEL_DOWNLOAD`: Set to "true" to force re-download models (default: false)

## GitHub Actions Workflow

This repository includes a GitHub Actions workflow that automatically builds and publishes the Docker image to Docker Hub whenever changes are pushed to the main branch.

### How it works

1. When code is pushed to the main branch, the workflow is triggered
2. The workflow builds the Docker image using the Dockerfile
3. The image is tagged and pushed to Docker Hub
4. The image is available at `promptalchemist/comfyui-docker-new:latest`

### Using the workflow

To use the GitHub Actions workflow:

1. Set up Docker Hub secrets in your GitHub repository:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Your Docker Hub access token
2. Push changes to the main branch to trigger the workflow
3. Check the "Actions" tab in your GitHub repository to monitor the build progress
4. Once complete, pull the image from Docker Hub

### Manual trigger

You can also manually trigger the workflow from the "Actions" tab in your GitHub repository.

## Development

To modify the Docker image:

1. Edit the `dockerfile` to add or change components
2. Update `models_config.json` to change which models are downloaded
3. Modify `start.sh` to change startup behavior
4. Push changes to GitHub to trigger the automatic build

## Directory Structure

```
hunyuan-comfyui-docker/
├── Dockerfile
├── models/                    # Local LORA models
├── scripts/
│   ├── download_models.py    # Model download script
│   ├── update.sh            # Update script
│   ├── start.sh             # Startup script
│   └── log_viewer.py        # Monitoring interface
├── models_config.json        # Model download configuration
└── README.md
```

## Accessing Services

- ComfyUI: `http://localhost:8188`
- Log Viewer: `http://localhost:8189`
- Jupyter Lab: `http://localhost:8888`

## Model Configuration

Edit `models_config.json` to configure model downloads:

```json
{
  "diffusion_models": [
    "https://huggingface.co/..."
  ],
  "unet": [
    "https://huggingface.co/..."
  ]
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| UPDATE_ON_START | Enable automatic updates | false |
| MODELS_CONFIG_URL | Custom model config URL | default config |
| SKIP_MODEL_DOWNLOAD | Skip model downloads | false |
| FORCE_MODEL_DOWNLOAD | Force model re-download | false |

## Requirements

- Docker with NVIDIA Container Toolkit
- NVIDIA GPU with CUDA support (RTX 4090 recommended)
- 20GB+ disk space
- 16GB+ RAM

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 