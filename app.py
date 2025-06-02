# app.py
import os
import json
import requests # Using requests library for HTTP calls
from dotenv import load_dotenv
import streamlit as st
import sqlite3 
import uuid    
import datetime 

# Load environment variables from .env file
load_dotenv()

# --- Configuration --- (Keep only ONE instance of this block)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
CHATBOT_NAME = "Membership & Subscription Assistant"
DOMAIN_CONTEXT = """
You are a customer service chatbot for a 'Membership and Subscription Manager' service.
Your primary goal is to assist users with inquiries related to managing their memberships and subscriptions.
This includes questions about:
- Signing up for new services
- Cancelling existing subscriptions
- Upgrading or downgrading membership plans
- Payment issues and billing inquiries
- Understanding membership benefits
- Troubleshooting account access
- Resetting passwords for the membership portal
- Finding information about specific subscription terms and conditions

Please keep your responses focused ONLY on these topics.
If a user asks something outside of this domain, you MUST politely state that you can only help with membership and subscription-related queries and cannot answer the out-of-domain request.
Do not attempt to answer questions outside this scope.
Be friendly, helpful, and concise in your answers within the defined domain.
If you provide lists, use hyphens or asterisks for bullet points.
Use bolding with double asterisks **like this** for emphasis if it's natural in the response.
"""

# --- Predefined FAQs ---
FAQS = {
    "how to cancel subscription": "You can cancel your subscription by going to your account settings page and clicking on 'Cancel Subscription'. Would you like a direct link to your account settings?",
    "cancel my membership": "To cancel your membership, please log in to your account, navigate to the 'Membership Details' section, and you should find an option to cancel. If you need further assistance, I can guide you.",
    "how to sign up": f"To sign up for a new membership, please visit our website's homepage and look for the 'Sign Up' or 'Join Now' button. You'll be guided through the process. Our service helps you manage all your various subscriptions in one place!",
    "payment methods": "We accept various payment methods including major credit cards (Visa, MasterCard, American Express) and PayPal. You can manage your payment methods in the 'Billing Information' section of your account.",
    "forgot password": "If you've forgotten your password, you can reset it by clicking the 'Forgot Password?' link on the login page. You'll receive an email with instructions to create a new password.",
    "contact support": "If you need to speak with a human support agent, you can usually find a 'Contact Us' or 'Support' link on our website, which may offer options like live chat, email, or a phone number.",
    "what is this service": f"This is the **{CHATBOT_NAME}**. I can help you manage your various memberships and subscriptions, answer questions about your account, billing, and service features.",
    "upgrade plan": "To upgrade your plan, please log into your account and go to the 'Subscription' or 'Plan Details' section. You should see options to upgrade to a higher tier. What specific plan are you interested in?",
    "billing issue": "I'm sorry to hear you're having a billing issue. Could you please provide more details about the problem? For example, are you seeing an incorrect charge, or is a payment failing?"
}
# (Ensure the duplicated Configuration block below this is removed from your actual file)

# --- Database Setup --- 
DB_NAME = "chatbot_history.db"

def init_db():
    """Initializes the database and creates the chat_logs table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL, 
        content TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

init_db() 
# --- End Database Setup ---

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +++ ADD THE save_message_to_db FUNCTION HERE +++
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def save_message_to_db(session_id, role, content):
    """Saves a chat message to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Using a specific timestamp when inserting
        current_timestamp = datetime.datetime.now()
        cursor.execute("INSERT INTO chat_logs (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                       (session_id, role, content, current_timestamp))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database error during save: {e}") 
    finally:
        if conn:
            conn.close()
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +++ END OF save_message_to_db FUNCTION +++
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# --- Streamlit Page Configuration ---
st.set_page_config(page_title=CHATBOT_NAME, page_icon="💬")
st.title(CHATBOT_NAME)

# --- Initialize session state for conversation history ---
# `gemini_history` stores the conversation in the format required by the Gemini API.
# `display_messages` stores messages for Streamlit's UI.

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +++ ADD SESSION ID INITIALIZATION HERE +++
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
if 'session_id' not in st.session_state: 
    st.session_state.session_id = str(uuid.uuid4())
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +++ END OF SESSION ID INITIALIZATION +++
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

if "gemini_history" not in st.session_state:
    st.session_state.gemini_history = [
        {"role": "user", "parts": [{"text": DOMAIN_CONTEXT}]},
        {"role": "model", "parts": [{"text": f"Understood. I am the **{CHATBOT_NAME}**. I will ONLY answer questions related to managing memberships and subscriptions as outlined. If a query is outside this scope, I will inform you that I cannot assist with it."}]}
    ]

if "display_messages" not in st.session_state:
    st.session_state.display_messages = [
        {"role": "assistant", "content": f"Hello! I am the **{CHATBOT_NAME}**. How can I help you with your memberships and subscriptions today?"}
    ]

# --- Display existing chat messages ---
for message in st.session_state.display_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"]) 

# --- Function to get bot response --- (This function remains the same as in your provided code)
def get_bot_response(user_message):
    # 1. Add user message to Gemini history (API format)
    st.session_state.gemini_history.append({"role": "user", "parts": [{"text": user_message}]})

    # 2. Check for FAQ match
    for keyword, answer in FAQS.items():
        if keyword in user_message.lower():
            bot_reply = answer
            st.session_state.gemini_history.append({"role": "model", "parts": [{"text": bot_reply}]})
            return bot_reply

    # 3. If no FAQ match, call Gemini API
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY not found. Please set it in your .env file.")
        return "Sorry, the chatbot is not configured correctly (missing API key)."

    try:
        payload = {
            "contents": st.session_state.gemini_history,
            "generationConfig": {
                "temperature": 0.6,
                "topK": 1,
                "topP": 0.95,
                "maxOutputTokens": 512, 
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
        }
        headers = {"Content-Type": "application/json"}
        response_api = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload), timeout=30) # Renamed response to response_api to avoid conflict
        response_api.raise_for_status()
        
        result = response_api.json()

        if (result.get("candidates") and
            result["candidates"][0].get("content") and
            result["candidates"][0]["content"].get("parts") and
            len(result["candidates"][0]["content"]["parts"]) > 0):
            bot_reply = result["candidates"][0]["content"]["parts"][0].get("text", "Sorry, I couldn't generate a response for that.")
        elif result.get("promptFeedback") and result["promptFeedback"].get("blockReason"):
            block_reason = result["promptFeedback"]["blockReason"]
            bot_reply = f"I am unable to respond to that request due to content restrictions ({block_reason}). Please ask a question related to memberships and subscriptions."
            st.warning(f"Gemini API blocked prompt. Reason: {block_reason}")
        else:
            bot_reply = "Sorry, I received an unexpected response from the AI. Please try asking in a different way."
            st.warning(f"Unexpected Gemini API response structure: {result}")

    except requests.exceptions.Timeout:
        st.error("Error: The request to the AI service timed out. Please try again shortly.")
        bot_reply = "Sorry, the request to my AI brain timed out."
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling Gemini API: {e}")
        bot_reply = "Sorry, I'm having trouble connecting to my brain right now. Please try again."
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        bot_reply = "An unexpected error occurred. Please try again."

    # 4. Add bot reply to Gemini history
    st.session_state.gemini_history.append({"role": "model", "parts": [{"text": bot_reply}]})
    
    # 5. Limit history size (for Gemini API)
    MAX_HISTORY_TURNS = 10 
    if len(st.session_state.gemini_history) > (MAX_HISTORY_TURNS * 2 + 2): 
        st.session_state.gemini_history = st.session_state.gemini_history[:2] + st.session_state.gemini_history[-(MAX_HISTORY_TURNS*2):]
    
    return bot_reply

# --- Handle Chat Input ---
if prompt := st.chat_input("Ask me about memberships or subscriptions..."):
    # Add user message to display messages
    st.session_state.display_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # +++ SAVE USER MESSAGE TO DB HERE +++
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    save_message_to_db(st.session_state.session_id, "user", prompt)
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # +++ END OF SAVE USER MESSAGE +++
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."): 
            response = get_bot_response(prompt) # 'response' here is the bot's text reply
        st.markdown(response) 

    # Add bot response to display messages
    st.session_state.display_messages.append({"role": "assistant", "content": response})

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # +++ SAVE BOT MESSAGE TO DB HERE +++
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    save_message_to_db(st.session_state.session_id, "assistant", response)
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # +++ END OF SAVE BOT MESSAGE +++
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# --- Instructions for running (optional, can be in a separate section or comments) ---
# (Your existing comments)