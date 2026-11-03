import streamlit as st
from genai import Client
from genai.errors import APIError
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import os

# 1. Page Configuration & Custom CSS for Modern ChatGPT Look
st.set_page_config(page_title="JIYA AI - Your Personal Assistant", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 2.5rem; font-weight: 700; color: #1E88E5; text-align: center; margin-bottom: 2rem; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; padding: 15px; }
    .stAudio { margin-top: 8px; }
</style>
""", unsafe_scale=True)

# 2. Secure API Key Initialization
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key and "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

# 3. Sidebar UI & Settings
with st.sidebar:
    st.title("🤖 JIYA AI Settings")
    st.caption("Complete Fresh Project v1.0")
    
    # Model Selection (Using official stable names)
    selected_model = st.selectbox(
        "Choose Gemini Model:",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0,
        help="Flash is faster for daily chat. Pro is better for complex tasks."
    )
    
    # System Instructions for Language Support
    system_instruction = (
        "You are JIYA, a helpful, friendly, and smart AI assistant. "
        "You seamlessly support Hindi, English, and Hinglish. Always respond politely "
        "in the language chosen by the user."
    )
    
    st.markdown("---")
    # Voice Output Toggle
    enable_voice = st.checkbox("🔊 Enable Voice Output (TTS)", value=False, help="Talk back in audio format")
    
    # Clear Chat Button
    if st.button("➕ New Chat / Clear History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.audio_processed = False
        st.rerun()

# 4. Initialize Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "audio_processed" not in st.session_state:
    st.session_state.audio_processed = False

# 5. Render Chat History (ChatGPT Style)
st.markdown("<h1 class='main-title'>🤖 JIYA AI Assistant</h1>", unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "audio" in message and message["audio"] is not None:
            st.audio(message["audio"], format="audio/mp3")

# Helper function to generate Text-to-Speech
def generate_tts(text_content):
    try:
        tts = gTTS(text=text_content, lang='hi', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception:
        return None

# Helper function to call Gemini API safely
def call_gemini(client, model, prompt, history):
    # Format history into the structure required by the new client
    contents = []
    for msg in history:
        contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
    # Add the current user prompt
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    
    # API Call with robust error handling
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config={"system_instruction": system_instruction}
        )
        if response and response.text:
            return response.text
        else:
            return "⚠️ Error: AI returned an empty response. Please try again."
    except APIError as e:
        if e.code == 403:
            return "🔒 Error: Invalid API Key. Please check your secrets.toml file."
        elif e.code == 429:
            return "⏳ Error: Rate limit exceeded. Too many requests. Please wait a moment."
        elif e.code == 503:
            return "🚧 Error: Gemini Service is temporarily unavailable. Try again later."
        else:
            return f"❌ API Error ({e.code}): {e.message}"
    except Exception as e:
        return f"🔌 Network or Connection Error: {str(e)}"

# 6. Input Section (Text Box + Microphone)
if not api_key:
    st.error("🔑 API Key Missing! Please add your GEMINI_API_KEY to `.streamlit/secrets.toml` to start chatting with JIYA.")
else:
    # Initialize the Google GenAI Client
    client = Client(api_key=api_key)
    
    # Layout for text input and voice input side by side
    col1, col2 = st.columns([0.85, 0.15])
    
    user_prompt = ""
    
    with col1:
        # Standard Text Chat Input
        text_input = st.chat_input("JIYA से कुछ पूछें (Ask in English, Hindi, or Hinglish)...")
        if text_input:
            user_prompt = text_input
            
    with col2:
        # Microphone Audio Input Widget
        st.write("🎙️ Voice:")
        audio_data = mic_recorder(
            start_prompt="Record",
            stop_prompt="Stop",
            key='mic',
            just_once=True
        )
        
        # Audio input triggers a placeholder process
        if audio_data and not st.session_state.audio_processed:
            st.session_state.audio_processed = True
            # For a pure audio assistant model, audio_data['bytes'] can be sent.
            # To keep it friendly for beginners, we ask them to use text or notify how it's captured.
            user_prompt = "Hello JIYA! (Audio input received via mic)"

    # 7. Processing the Prompt & Response Generation
    if user_prompt:
        # Append User Message to UI
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
            
        # Generate Response from Gemini
        with st.chat_message("model"):
            with st.spinner("JIYA सोच रही है... 🤔"):
                ai_response = call_gemini(client, selected_model, user_prompt, st.session_state.messages[:-1])
                st.markdown(ai_response)
                
                # Handle Voice Output if enabled
                audio_bytes = None
                if enable_voice and not ai_response.startswith("⚠️") and not ai_response.startswith("❌"):
                    audio_bytes = generate_tts(ai_response)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                
                # Save to session history
                st.session_state.messages.append({
                    "role": "model", 
                    "content": ai_response,
                    "audio": audio_bytes
                })
        
        # Reset audio processing lock for next turn
        st.session_state.audio_processed = False
