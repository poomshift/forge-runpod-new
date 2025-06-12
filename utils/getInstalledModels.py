import os


def get_installed_models():
    """Get a list of installed models from models_config.json"""
    models = {}

    try:
        # Check multiple possible locations for models_config.json
        config_paths = [
            "/workspace/models_config.json",
            "./models_config.json",
            os.path.join(os.path.dirname(__file__), "models_config.json"),
        ]

        model_config = None
        for path in config_paths:
            if os.path.exists(path):
                import json

                with open(path, "r") as file:
                    model_config = json.load(file)
                break

        if not model_config:
            print("Warning: models_config.json not found in expected locations")
            return {}

        # Process each model category
        for category, urls in model_config.items():
            if urls:  # Only process non-empty categories
                model_files = []
                for url in urls:
                    # Extract filename from URL
                    filename = url.split("/")[-1]

                    # Add model information
                    model_files.append(
                        {
                            "name": filename,
                            "path": f"/workspace/stable-diffusion-webui-forge/models/{category}/{filename}",
                            "url": url,
                        }
                    )

                if model_files:
                    # Sort by name
                    model_files.sort(key=lambda x: x["name"].lower())
                    models[category] = model_files
    except Exception as e:
        print(f"Error parsing models from models_config.json: {e}")

    # Sort categories alphabetically
    return dict(sorted(models.items()))
