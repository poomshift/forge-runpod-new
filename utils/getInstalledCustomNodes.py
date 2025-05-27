import os


def get_installed_custom_nodes():
    """Get a list of installed custom nodes from start.sh"""
    custom_nodes = []

    try:
        # Check multiple possible locations for start.sh
        start_sh_paths = [
            "/start.sh",
            "./start.sh",
            "/workspace/start.sh",
            os.path.join(os.path.dirname(__file__), "start.sh"),
        ]
        start_sh_content = None

        for path in start_sh_paths:
            if os.path.exists(path):
                with open(path, "r") as file:
                    start_sh_content = file.read()
                break

        if not start_sh_content:
            print("Warning: start.sh not found in expected locations")
            return []

        # Extract git clone lines for custom nodes
        import re

        pattern = r"git clone --depth=1 (https://github.com/[^/]+/([^\.]+)\.git)"
        matches = re.findall(pattern, start_sh_content)

        for match in matches:
            repo_url, repo_name = match
            # Extract the actual repository name from the URL
            repo_name_clean = repo_url.split("/")[-1].replace(".git", "")

            custom_nodes.append(
                {
                    "name": repo_name_clean,
                    "path": f"/workspace/ComfyUI/custom_nodes/{repo_name_clean}",
                    "version": "Installed",
                    "url": repo_url,
                }
            )
    except Exception as e:
        print(f"Error parsing custom nodes from start.sh: {e}")

    # Sort alphabetically
    return sorted(custom_nodes, key=lambda x: x["name"].lower())
