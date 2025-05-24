#!/bin/bash
# Enhanced script for setting up virtual environment with all dependencies

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the virtual environment directory
VENV_DIR=".venv"
# Define the path to the activate script for clarity
VENV_ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"

# --- Python Version Check ---
echo "Checking Python version..."
python_version_full=$(python3 --version 2>&1) # Get full version string e.g., "Python 3.11.2"
if [[ ! "$python_version_full" =~ Python\ ([0-9]+)\.([0-9]+)\.?([0-9]*) ]]; then
    echo "Error: Could not parse Python version from '$python_version_full'."
    exit 1
fi
python_version_detected="${BASH_REMATCH[0]}" # Full match e.g., "Python 3.11.2"
major_version="${BASH_REMATCH[1]}"
minor_version="${BASH_REMATCH[2]}"
echo "Detected $python_version_detected"

# Require Python 3.9 or higher
if [ "$major_version" -lt 3 ] || { [ "$major_version" -eq 3 ] && [ "$minor_version" -lt 9 ]; }; then
    echo "Error: Python 3.9 or higher is required. Detected $major_version.$minor_version."
    exit 1
fi
echo "Python version check passed."

# --- Virtual Environment Setup ---
# Check if the virtual environment needs to be created or cleared and recreated.
# We primarily check for the existence of the activate script.
if [ ! -f "$VENV_ACTIVATE_SCRIPT" ]; then
    echo "Virtual environment activation script ($VENV_ACTIVATE_SCRIPT) not found."
    echo "Attempting to create/recreate virtual environment in '$VENV_DIR'..."

    # Ensure the base directory for the venv exists.
    # Docker volume mount should create it, but this is a good safeguard.
    mkdir -p "$VENV_DIR"
    echo "Ensured directory $VENV_DIR exists."

    # If the directory exists and has contents (but no activate script, or we want to refresh),
    # clear its contents. This is crucial for Docker volume mounts.
    if [ -d "$VENV_DIR" ] && [ "$(ls -A "$VENV_DIR")" ]; then
        echo "Clearing contents of existing $VENV_DIR..."
        # Use find to delete all files and subdirectories within VENV_DIR
        # -mindepth 1 ensures we don't try to delete VENV_DIR itself.
        find "$VENV_DIR" -mindepth 1 -delete
        echo "Contents of $VENV_DIR cleared."
    fi
    
    echo "Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    echo "Python virtual environment created in $VENV_DIR."
else
    echo "Virtual environment at $VENV_DIR with activation script $VENV_ACTIVATE_SCRIPT appears to exist."
    echo "Proceeding to activate and update dependencies."
fi

# --- Activate Virtual Environment ---
if [ ! -f "$VENV_ACTIVATE_SCRIPT" ]; then
    echo "ERROR: Virtual environment activation script ($VENV_ACTIVATE_SCRIPT) still missing after creation attempt!"
    exit 1
fi
echo "Activating virtual environment from $VENV_ACTIVATE_SCRIPT..."
source "$VENV_ACTIVATE_SCRIPT"
echo "Virtual environment activated."

# --- Install/Upgrade Dependencies ---
echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Skipping dependency installation."
fi

if [ -f "requirements-dev.txt" ]; then
    echo "Installing development dependencies from requirements-dev.txt..."
    pip install -r requirements-dev.txt
else
    echo "Info: requirements-dev.txt not found. Skipping development dependencies."
fi

echo "Installing project in editable mode (pip install -e .)..."
# This assumes your project has a setup.py or pyproject.toml for editable installs.
# If not, this command might not be necessary or could fail.
# Consider adding a check for setup.py or pyproject.toml if this is optional.
pip install -e .

# --- Verification (Optional) ---
# This is an example; adjust as needed for your project.
if python -c "from app import __version__" &> /dev/null; then
    echo "Verifying installation..."
    app_version=$(python -c "from app import __version__; print(__version__)")
    echo "Application version: $app_version"
else
    echo "Info: Could not import __version__ from app. Skipping version verification."
fi


# --- Pre-commit Hooks (Optional) ---
if [ -f ".pre-commit-config.yaml" ]; then
    echo "Setting up pre-commit hooks..."
    # Ensure pre-commit is installed
    if ! command -v pre-commit &> /dev/null; then
        echo "pre-commit not found, installing..."
        pip install pre-commit
    fi
    pre-commit install
    echo "Pre-commit hooks installed."
else
    echo "Info: .pre-commit-config.yaml not found. Skipping pre-commit setup."
fi

echo "Virtual environment setup and dependency installation complete."
echo "The environment is active within this script's execution context (and for the uvicorn command in docker-compose)."
