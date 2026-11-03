import streamlit as st
import os
import base64
from google import genai
from google.genai import types
from google.genai.errors import APIError

# ============================================================================
# 1. PAGE CONFIGURATION & STYLING
# ============================================================================
st.set_page_config(
    page_title="JIYA AI - Personal Assistant",
    page_icon="✨",
    layout="wide"
)

# Custom CSS for UI layout
st.markdown("""
<style>
    .main-title { font-size: 2.5rem; font-weight: bold; margin-bottom: 0px; }
    .subtitle { color: #888; font-size: 1rem; margin-bottom: 20px; }
    .stChatInputContainer { padding-bottom: 20px; }
</style>
""", unsafe_scale=True)

# ============================================================================
# 2. SESSION STATE INITIALIZATION (Avoids Duplicates & Retains History)
# ============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_processed_prompt" not in st.session_state:
    st.session_state.last_processed_prompt = None

if "speak_queue" not in st.session_state:
    st.session_state.speak_queue = None

# ============================================================================
# 3. API INITIALIZATION (Google GenAI SDK)
# ============================================================================
@st.cache_resource
def get_genai_client():
    """Initializes and caches the Gemini Client using Streamlit Secrets securely."""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            st.error("❌ GEMINI_API_KEY missing in Streamlit Secrets! Check deployment steps below.")
            return None
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Initialization Error: {str(e)}")
        return None

client = get_genai_client()

# Default recommended current model name (Fast, powerful, and free-tier accessible)
DEFAULT_MODEL = "gemini-2.5-flash"

# ============================================================================
# 4. SYSTEM PROMPT (JIYA's Personality & Core Directives)
# ============================================================================
JIYA_SYSTEM_INSTRUCTION = """
You are JIYA, a friendly, highly intelligent female personal AI assistant.
Your traits:
- Speak naturally in Hindi, Hinglish, or English depending on how the user greets you.
- Always be soft-spoken, extremely polite, deeply caring, and genuinely helpful.
- Assist cleanly with CDS (Combined Defence Services) exam preparation, coding tasks, conceptual learning, and daily productivity questions.
- Keep simple answers clear, direct, and short to optimize response times.
- Avoid unnecessary preambles unless asked. Keep tone encouraging.
"""

# ============================================================================
# 5. VOICE FEATURES (Web Speech API Browser Synthesis)
# ============================================================================
def generate_browser_tts(text: str):
    """Generates an immediate client-side Javascript text-to-speech triggers."""
    # Escape quotes cleanly to avoid breaking Javascript strings
    clean_text = text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
    
    js_script = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel(); // Stop current speech
            var msg = new SpeechSynthesisUtterance('{clean_text}');
            var voices = window.speechSynthesis.getVoices();
            
            // Attempt to find a suitable Indian English or Hindi female voice accent
            var targetVoice = voices.find(function(v) {{
                return (v.lang.includes('en-IN') || v.lang.includes('hi-IN')) && v.name.toLowerCase().includes('female');
            }}) || voices.find(function(v) {{
                return v.name.toLowerCase().includes('female') || v.lang.includes('en');
            }});
            
            if (targetVoice) msg.voice = targetVoice;
            msg.rate = 1.0;
            msg.pitch = 1.0;
            window.speechSynthesis.speak(msg);
        }}
    </script>
    """
    st.components.v1.html(js_script, height=0, width=0)

def stop_browser_tts():
    """Immediately kills any ongoing audio playback in the browser window."""
    js_script = """
    <script>
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    </script>
    """
    st.components.v1.html(js_script, height=0, width=0)

# ============================================================================
# 6. SIDEBAR CONTROLS & MODEL SELECTION
# ============================================================================
with st.sidebar:
    st.markdown("## ⚙️ JIYA Settings")
    
    # Model fallback selector allowing runtime updates without key alterations
    selected_model = st.text_input(
        "Active Gemini Model", 
        value=DEFAULT_MODEL,
        help="To change the model dynamically, replace this text string (e.g., 'gemini-1.5-flash')."
    )
    
    st.markdown("---")
    st.markdown("### 🔊 Voice Controls")
    speak_replies = st.checkbox("Speak replies automatically", value=True, id="speak_replies_chk")
    
    if st.button("⏹️ Stop Speaking", use_container_width=True):
        stop_browser_tts()
        
    st.markdown("---")
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_processed_prompt = None
        st.session_state.speak_queue = None
        stop_browser_tts()
        st.rerun()

# ============================================================================
# 7. MAIN INTERFACE
# ============================================================================
st.markdown('<div class="main-title">✨ JIYA AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Your personal AI • Voice • Hindi / Hinglish / English</div>', unsafe_allow_html=True)

# Render established chat memory container cleanly
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Trigger speech execution cleanly post-render loop to ensure script injection fires properly
if st.session_state.speak_queue:
    generate_browser_tts(st.session_state.speak_queue)
    st.session_state.speak_queue = None

# Audio input module configuration
st.markdown("### 🎤 Voice Input (Optional)")
audio_file = st.audio_input("Record your question for JIYA here:")

# Initialize input variables
user_prompt = None
audio_bytes = None

# Handle user microphone input strictly once
if audio_file is not None:
    audio_bytes = audio_file.read()
    # Unique identifier check based on length to prevent infinite multi-render re-runs
    audio_id = f"audio_{len(audio_bytes)}"
    if st.session_state.last_processed_prompt != audio_id:
        user_prompt = "[Audio Message Processed]"
        st.session_state.last_processed_prompt = audio_id

# Handle traditional text box chat input alternate
text_input = st.chat_input("Message JIYA...")
if text_input:
    user_prompt = text_input

# ============================================================================
# 8. RESPONSE INFERENCE ENGINE (Optimized Fast Loop)
# ============================================================================
if user_prompt and client:
    
    # 1. Append user query instantly to UI interface
    if audio_bytes and user_prompt == "[Audio Message Processed]":
        display_text = "🎤 *Sent an audio message...*"
        st.session_state.messages.append({"role": "user", "content": display_text})
        with st.chat_message("user"):
            st.markdown(display_text)
    else:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

    # 2. Build contents payload correctly mapping historical arrays
    contents_payload = []
    
    # Pack historical tracking messages into compliant structural types
    for m in st.session_state.messages[:-1]:
        role_label = "user" if m["role"] == "user" else "model"
        # Skip internal status messages from being fed to context window
        if "🎤 *Sent an audio message...*" in m["content"]:
            continue
        contents_payload.append(
            types.Content(role=role_label, parts=[types.Part.from_text(text=m["content"])])
        )
    
    # Format incoming active prompt parameters cleanly
    if audio_bytes and user_prompt == "[Audio Message Processed]":
        # Package raw microphone binary accurately to match Parts requirements
        active_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
        contents_payload.append(types.Content(role="user", parts=[active_part]))
    else:
        contents_payload.append(types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]))

    # 3. Dispatch execution to Google GenAI server with localized spinner controls
    with st.chat_message("model"):
        with st.spinner("JIYA is thinking..."):
            try:
                # Optimized configuration settings maps direct structure mapping fast replies
                config = types.GenerateContentConfig(
                    system_instruction=JIYA_SYSTEM_INSTRUCTION,
                    max_output_tokens=600,  # Limits lengthy outputs to enforce speed
                    temperature=0.7
                )
                
                response = client.models.generate_content(
                    model=selected_model,
                    contents=contents_payload,
                    config=config
                )
                
                ai_reply = response.text if response.text else "Jiya couldn't generate text response."
                
                st.markdown(ai_reply)
