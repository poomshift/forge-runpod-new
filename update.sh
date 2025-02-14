#!/bin/bash
echo "Updating ComfyUI and custom nodes..."

# Update ComfyUI
cd /workspace/ComfyUI
git pull
pip install -r requirements.txt

# Update custom nodes
cd custom_nodes

for d in */ ; do
    if [ -d "$d/.git" ]; then
        echo "Updating $d..."
        cd "$d"
        git pull
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        fi
        cd ..
    fi
done

echo "Update completed." 