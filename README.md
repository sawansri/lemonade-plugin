# Lemonade Control Panel

A simple Open WebUI Action for managing [Lemonade Server](https://lemonade-server.ai/) instances.

## Features

*   **System Overview**: Leave the input empty to view a combined report of Health, Stats, System Info, and Installed Models.
*   **Model Management**: Interactive prompts for `pull` and `delete` commands that list available models before execution.

## Usage

1.  Activate the **Lemonade Control Panel** action in your chat.
2.  When prompted for input:
    *   **Leave Empty**: Generates a full system dashboard.
    *   **pull**: Lists all available remote models and prompts for a Model ID to download.
    *   **delete**: Lists all installed models and prompts for a Model ID to remove.
    *   **health** / **stats**: Queries specific endpoints.

## Configuration

Configure the following settings in the **Valves** menu:

*   **BASE_URL**: The address of the Lemonade server (default: `http://localhost:8000`).
*   **TIMEOUT_SECONDS**: Default timeout for standard requests (default: `20`).
