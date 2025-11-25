# Telegram-Google-Gemini Agent (MCP)

This project implements an intelligent agent that integrates **Telegram**, **Google Workspace** (Sheets, Gmail, Drive), and **Google Gemini LLM** using the **Model Context Protocol (MCP)**.

## Features

*   **Telegram Integration**: Receives messages from users via a Telegram Bot.
*   **Gemini AI**: Processes user queries using Google's Gemini Pro model (`gemini-2.0-flash` or `gemini-1.5-flash`).
*   **Google Sheets**: Automatically logs user queries and AI responses to a Google Sheet.
*   **Gmail Notification**: Sends an email notification with the query, response, and a direct link to the Google Sheet.
*   **MCP Architecture**: Built using `FastMCP` with separate servers for Telegram (SSE) and Google Workspace (Stdio).

## Prerequisites

*   Python 3.13+
*   `uv` package manager (recommended)
*   A Telegram Bot Token (from @BotFather)
*   Google Cloud Project with APIs enabled:
    *   Google Sheets API
    *   Google Drive API
    *   Gmail API
*   Google Gemini API Key

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies**:
    ```bash
    uv sync
    # OR
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    GOOGLE_CREDENTIALS_FILE=credentials.json
    TARGET_GMAIL_ADDRESS=your_email@gmail.com
    GEMINI_API_KEY=your_gemini_api_key
    SPREADSHEET_ID=optional_spreadsheet_id
    ```

4.  **Google Auth Setup**:
    *   Place your `credentials.json` (OAuth 2.0 Client ID) in the root folder.
    *   Ensure your Google Cloud Project has the required APIs enabled.
    *   **Important**: If your project is in "Testing" mode, add your email to the "Test Users" list in the OAuth Consent Screen.

## Usage

1.  **Start the Telegram MCP Server**:
    ```bash
    uv run mcp_server_telegram.py
    ```

2.  **Start the Main Agent**:
    In a separate terminal:
    ```bash
    uv run main_agent.py
    ```

3.  **Interact**:
    *   Send a message to your Telegram Bot.
    *   The agent will process it with Gemini.
    *   It will append the result to your Google Sheet.
    *   You will receive an email with the details.

## Troubleshooting

### Google 403 "Permission Denied" Error
If you see a 403 error when creating or accessing sheets:
1.  **Check API Enablement**: Ensure "Google Sheets API" is enabled in your Google Cloud Console for the *correct* project.
2.  **Check Scopes**: When signing in, make sure to check **ALL** the permission boxes (Drive, Sheets, Gmail).
3.  **Drive Storage**: Ensure your Google Drive is not full.
4.  **Workaround**: Manually create a sheet, copy its ID, and add `SPREADSHEET_ID=your_id` to your `.env` file.

### Gemini 404/429 Errors
*   **404**: The model name might be incorrect. Try `gemini-1.5-flash` or `gemini-2.0-flash`.
*   **429**: You are hitting rate limits. Wait a moment or switch to a smaller model.
