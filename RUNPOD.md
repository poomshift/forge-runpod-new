# Hunyuan ComfyUI RunPod Template

This template provides a ready-to-use Hunyuan video generation environment on RunPod, featuring ComfyUI with real-time monitoring and automatic model management.

## Template Features

- **Pre-configured Environment**: All necessary dependencies and custom nodes installed
- **Real-time Monitoring**: Web-based interface for system monitoring and log viewing
- **Dynamic Model Management**: Automatic model downloads from configurable sources
- **Jupyter Integration**: Built-in Jupyter Lab for development
- **Auto-Update System**: Optional automatic updates for ComfyUI and custom nodes

## Quick Start

1. **Select Template**:
   - Go to RunPod.io dashboard
   - Click "Deploy"
   - Select "Custom Template"
   - Enter Docker image: `[your-image-name]`

2. **Configure Pod**:
   - **GPU**: Select RTX 4090 or better (recommended)
   - **Storage**: Minimum 20GB
   - **Ports**: The template automatically exposes:
     ```
     8188/http (ComfyUI)
     8189/http (Log Viewer)
     8888/http (Jupyter Lab)
     ```

3. **Environment Variables** (Optional):
   ```
   UPDATE_ON_START=true         # Enable automatic updates
   MODELS_CONFIG_URL=<url>      # Custom model config URL
   SKIP_MODEL_DOWNLOAD=true     # Skip model downloads
   FORCE_MODEL_DOWNLOAD=true    # Force model re-download
   ```

4. **Deploy and Access**:
   - Click "Deploy"
   - Wait for pod initialization
   - Access services through RunPod console:
     - ComfyUI: Click port 8188
     - Log Viewer: Click port 8189
     - Jupyter Lab: Click port 8888

## Pre-installed Components

### Custom Nodes
- ComfyUI-Manager (Node management)
- ComfyUI-HunyuanVideoWrapper (Hunyuan integration)
- VideoHelperSuite (Video processing)
- ComfyUI-TeaCacheHunyuanVideo (Caching)
- Comfy-WaveSpeed (Performance optimization)
- Additional utility nodes

### Models
- Hunyuan Video Models:
  - `hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors`
  - `fast-hunyuan-video-t2v-720p-Q4_K_M.gguf`
  - `hunyuan_video_vae_bf16.safetensors`
- Text Encoders:
  - `clip_l.safetensors`
  - `llava_llama3_fp8_scaled.safetensors`
- LORA Models:
  - `studio_ghibli_hv_v03_19.safetensors`
  - `hunyuan_flat_color_v2.safetensors`

## Volume Management

### Persistent Storage
Mount volumes to preserve data between pod restarts:
- Models: `/workspace/ComfyUI/models`
- Outputs: `/workspace/ComfyUI/output`
- Custom Nodes: `/workspace/ComfyUI/custom_nodes`

### Template Volumes
The template includes pre-configured volume paths:
```
/workspace/
├── ComfyUI/
│   ├── models/
│   ├── custom_nodes/
│   ├── input/
│   └── output/
└── logs/
```

## Monitoring & Management

### Log Viewer (Port 8189)
- Real-time system monitoring
- Resource usage graphs (CPU, RAM, GPU, Disk)
- Live ComfyUI log viewing
- Process control (Start/Stop ComfyUI)
- One-click output download

### Jupyter Lab (Port 8888)
- Development environment
- File management
- Terminal access
- Notebook support

## Performance Optimization

### Recommended Settings
- **GPU**: RTX 4090 or better
- **RAM**: 16GB minimum
- **Storage**: 20GB minimum
- **Network**: High-speed connection for model downloads

### Tips
1. Use persistent storage for models to avoid re-downloads
2. Enable caching for better performance
3. Monitor GPU memory usage through Log Viewer
4. Use FastHunyuan for better inference speed

## Troubleshooting

### Common Issues
1. **Model Download Failures**:
   - Check network connectivity
   - Verify model URLs in config
   - Ensure sufficient disk space
   - Try FORCE_MODEL_DOWNLOAD=true

2. **Performance Issues**:
   - Monitor GPU usage in Log Viewer
   - Check available VRAM
   - Adjust batch sizes
   - Enable caching

3. **Port Access**:
   - Verify port forwarding in RunPod console
   - Check pod status
   - Restart pod if needed

4. **Updates Failing**:
   - Check internet connectivity
   - Verify git repository access
   - Ensure sufficient disk space

## Security Notes

- Jupyter Lab runs without authentication (development setup)
- Consider setting custom tokens for production use
- All services exposed on 0.0.0.0
- Use secure model config URLs (HTTPS)

## Support

For issues and feature requests:
1. Check the troubleshooting guide
2. Visit the GitHub repository
3. Contact RunPod support for platform-specific issues 