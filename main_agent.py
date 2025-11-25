import asyncio
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in .env")

TELEGRAM_SSE_URL = "http://localhost:8000/sse"
GOOGLE_SERVER_SCRIPT = "mcp_server_google.py"

async def run_agent():
    print("Starting Agent...")
    
    async with AsyncExitStack() as stack:
        # Connect to Google MCP (Stdio)
        print(f"Connecting to Google MCP via Stdio ({GOOGLE_SERVER_SCRIPT})...")
        google_server_params = StdioServerParameters(
            command=sys.executable,
            args=[GOOGLE_SERVER_SCRIPT],
            env=os.environ.copy()
        )
        google_transport = await stack.enter_async_context(stdio_client(google_server_params))
        google_session = await stack.enter_async_context(ClientSession(google_transport[0], google_transport[1]))
        await google_session.initialize()
        print("Connected to Google MCP.")

        # Connect to Telegram MCP (SSE)
        print(f"Connecting to Telegram MCP via SSE ({TELEGRAM_SSE_URL})...")
        # Note: In a real scenario, we might need to retry connection if server isn't up yet
        try:
            telegram_transport = await stack.enter_async_context(sse_client(TELEGRAM_SSE_URL))
            telegram_session = await stack.enter_async_context(ClientSession(telegram_transport[0], telegram_transport[1]))
            await telegram_session.initialize()
            print("Connected to Telegram MCP.")
        except Exception as e:
            print(f"Failed to connect to Telegram MCP: {e}")
            print("Make sure mcp_server_telegram.py is running!")
            return

        # Main Loop
        print("Agent is running and listening for messages...")
        while True:
            try:
                # Poll for new messages
                result = await telegram_session.call_tool("get_next_message", arguments={})
                message_data = result.content[0].text
                
                if message_data != "NO_MESSAGES":
                    print(f"\nNew Message Received: {message_data}")
                    
                    # Parse message (simple eval for dict string, be careful in prod)
                    try:
                        msg_dict = eval(message_data)
                        user_text = msg_dict.get("text", "")
                        chat_id = msg_dict.get("chat_id")
                        user_name = msg_dict.get("user")
                    except:
                        print("Error parsing message data")
                        continue

                    # 1. Process with LLM
                    print(f"Sending query to Gemini: {user_text}")
                    try:
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        response = model.generate_content(user_text)
                        llm_response = response.text
                    except Exception as e:
                        print(f"Gemini Error: {e}")
                        llm_response = f"Error processing with Gemini: {e}"
                        try:
                            print("Attempting to list available models...")
                            for m in genai.list_models():
                                if 'generateContent' in m.supported_generation_methods:
                                    print(m.name)
                        except Exception as list_e:
                            print(f"Could not list models: {list_e}")
                    
                    print(f"LLM Response: {llm_response}")

                    # 2. Update Google Sheet
                    spreadsheet_id = os.getenv("SPREADSHEET_ID")
                    if not spreadsheet_id or spreadsheet_id == "your_spreadsheet_id_here":
                        print("No Spreadsheet ID found. Creating a new sheet...")
                        create_result = await google_session.call_tool("create_sheet", arguments={
                            "title": f"Agent Tasks - {user_name}"
                        })
                        new_id = create_result.content[0].text
                        if "Error" in new_id:
                            print(f"Failed to create sheet: {new_id}")
                            continue
                        
                        print(f"Created new sheet with ID: {new_id}")
                        # Update env var in memory for this session
                        os.environ["SPREADSHEET_ID"] = new_id
                        spreadsheet_id = new_id
                        
                        # Optional: Update .env file persistently
                        # with open(".env", "a") as f:
                        #    f.write(f"\nSPREADSHEET_ID={new_id}")

                    if spreadsheet_id:
                        print(f"Updating Google Sheet ({spreadsheet_id})...")
                        sheet_result = await google_session.call_tool("append_to_sheet", arguments={
                            "spreadsheet_id": spreadsheet_id,
                            "values": [user_name, user_text, llm_response]
                        })
                        print(f"Sheet Update: {sheet_result.content[0].text}")

                    # 3. Send Email
                    target_email = os.getenv("TARGET_GMAIL_ADDRESS")
                    if target_email:
                        print("Sending Email...")
                        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
                        email_result = await google_session.call_tool("send_email_with_attachment", arguments={
                            "to_email": target_email,
                            "subject": f"New Agent Task from {user_name}",
                            "body": f"User Query: {user_text}\n\nAgent Response: {llm_response}\n\nView in Google Sheets: {sheet_url}"
                        })
                        print(f"Email Status: {email_result.content[0].text}")

                    # 4. Reply on Telegram
                    await telegram_session.call_tool("send_reply", arguments={
                        "chat_id": chat_id,
                        "text": f"Processed your request: {llm_response}"
                    })
                    
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error in loop: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_agent())
