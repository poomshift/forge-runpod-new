# Stable Diffusion WebUI Forge RunPod Template

This project is a RunPod template for deploying [Stable Diffusion WebUI Forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) with:
- Automated model downloading via `models_config.json` (models are placed in Forge's expected folders)
- Jupyter Lab for notebooks
- Log viewer for monitoring

## Usage
- Models are specified in `models_config.json` and will be downloaded to the correct folders for Forge.
- Jupyter Lab is available on port 8888.
- Forge UI is available on port 7860.
- Log viewer is available on port 8189.

## 🌟 Features

- **Modern, Clean UI** - Intuitive interface with tabbed sections and responsive design
- **Real-time Log Viewer** - Docker-style formatted logs with auto-scroll functionality
- **Model Management** - Download models from Civitai, Hugging Face, and Google Drive
- **Pre-installed Custom Nodes** - Extensive collection of the most popular custom nodes
- **One-click Access** - Direct links to ComfyUI and JupyterLab interfaces
- **Output Download** - Quickly download all your generated images in one click

## 🚀 Getting Started

### Starting Your Pod

1. Select this template from the RunPod template library
2. Choose your desired GPU type (recommended at least 24GB VRAM for optimal performance)
3. Start your pod
4. Access the Dashboard at port 8189 from your pod's Connect tab

### Interface Overview

The interface consists of several key sections:

- **Top Controls** - Access links to ComfyUI, JupyterLab, and output downloads
- **Pre-installed Section** - View all custom nodes and models included in the template
- **Logs Section** - Monitor the ComfyUI logs in real-time with auto-scroll
- **Model Downloaders** - Download additional models from popular repositories

## 💾 Model Management

### Available Model Categories

- Checkpoints
- VAE
- LoRA
- UNet
- Diffusion Models
- Text Encoders
- Upscale Models
- CLIP
- ControlNet
- CLIP Vision
- IPAdapter
- Style Models

### Downloading Models

#### From Civitai

1. Navigate to the Civitai downloader tab
2. Enter the model URL from Civitai
3. Add your Civitai API key (optional)
4. Select the appropriate model type
5. Click "Download Model"

#### From Hugging Face

1. Navigate to the Hugging Face downloader tab
2. Enter the direct file URL from Hugging Face
3. Select the appropriate model type
4. Click "Download Model"

#### From Google Drive

1. Navigate to the Google Drive downloader tab
2. Enter the Google Drive URL or file ID
3. Select the appropriate model type
4. Optionally specify a custom filename
5. Click "Download Model"

## 🧩 Custom Nodes

This template comes with the following custom nodes pre-installed:

- ComfyUI-Manager
- ComfyUI-Impact-Pack
- ComfyUI_essentials
- ComfyUI-Inspire-Pack
- comfyui_controlnet_aux
- DZ-FaceDetailer
- ComfyUI_IPAdapter_plus
- ComfyUI_UltimateSDUpscale
- ComfyUI-VideoHelperSuite
- comfyui-inpaint-nodes
- ComfyUI-KJNodes
- ComfyUI-GGUF
- rgthree-comfy
- ComfyUI_Custom_Nodes_AlekPet
- ComfyUI-Gemini-API
- ComfyUI-RED-UNO
- Bjornulf_custom_nodes
- ComfyUI-Custom-Scripts


### Backing Up Your Work

To back up your work:
1. Use the "Download Outputs" button to get generated images
2. For workflows, save them through the ComfyUI interface


## 🙏 Acknowledgements

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) by comfyanonymous
- All custom node developers for their valuable contributions
- RunPod.io for the GPU cloud infrastructure

For more information, visit [PromptAlchemist on Facebook](https://www.facebook.com/PromptAlchemist). 