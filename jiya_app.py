
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
import json

# ---------------- APP SETTINGS ----------------
st.set_page_config(
    page_title="JIYA Personal AI",
    page_icon="💜",
    layout="centered"
)

MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """
You are JIYA, a friendly personal AI assistant.

Personality:
- Speak like a warm, caring, intelligent female assistant.
- Use natural Hindi and Hinglish when the user speaks Hindi.
- Use simple English when the user speaks English.
- Be polite, friendly, soft, and helpful.
- Keep answers clear and easy to understand.
- Help with daily tasks, learning, coding, and CDS preparation.
- Never claim that you physically control a device unless an actual
  connected integration confirms the action.
"""

# ---------------- SESSION MEMORY ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True

# ---------------- HEADER ----------------
st.title("💜 JIYA Personal AI")
st.caption("Your friendly AI assistant")

st.markdown(
    """
    **Hello Ashish! 😊**

    Main JIYA hoon. Tum mujhse Hindi, Hinglish ya English mein
    baat kar sakte ho.
    """
)

# ---------------- SETTINGS ----------------
with st.expander("⚙️ JIYA Settings"):
    st.session_state.voice_enabled = st.toggle(
        "Speak AI replies",
        value=st.session_state.voice_enabled
    )

    st.caption(
        "Soft female voice browser mein available voices se select hogi."
    )

    if st.button("🛑 Stop Speaking"):
        components.html(
            """
            <script>
            window.speechSynthesis.cancel();
            </script>
            """,
            height=0
        )

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ---------------- API KEY ----------------
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = ""

if not API_KEY:
    st.error("GEMINI_API_KEY missing hai.")

    st.info(
        """
        Streamlit Cloud → App Settings → Secrets

        Add:

        GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
        """
    )

    st.stop()

# ---------------- GEMINI CLIENT ----------------
@st.cache_resource
def get_client(api_key):
    return genai.Client(api_key=api_key)

client = get_client(API_KEY)

# ---------------- VOICE OUTPUT ----------------
def speak_text(text):
    safe_text = json.dumps(text, ensure_ascii=False)

    components.html(
        f"""
        <script>
        const textToSpeak = {safe_text};

        function speakJiya() {{
            if (!("speechSynthesis" in window)) {{
                return;
            }}

            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(
                textToSpeak
            );

            utterance.lang = "en-IN";
            utter.rate = 0.90;
            utter.pitch = 1.10;
            utter.volume = 1.0;

            const voices = window.speechSynthesis.getVoices();

            const femaleVoice = voices.find(v =>
                /female|zira|samantha|aria|heera|priya|veena/i
                .test(v.name)
            );

            const indianVoice = voices.find(v =>
                /en-IN|hi-IN/i.test(v.lang)
            );

            if (femaleVoice) {{
                utterance.voice = femaleVoice;
            }} else if (indianVoice) {{
                utterance.voice = indianVoice;
            }}

            window.speechSynthesis.speak(utterance);
        }}

        if (window.speechSynthesis.getVoices().length > 0) {{
            speakJiya();
        }} else {{
            window.speechSynthesis.onvoiceschanged = speakJiya;
        }}
        </script>
        """,
        height=0
    )

# ---------------- CHAT DISPLAY ----------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------------- USER TEXT INPUT ----------------
prompt = st.chat_input("💬 JIYA se kuch bhi pucho...")

# ---------------- MICROPHONE INPUT ----------------
audio_input = st.audio_input("🎤 Ya mic se apna question record karo")

user_text = None
audio_bytes = None
audio_mime = None

if prompt:
    user_text = prompt

elif audio_input is not None:
    audio_bytes = audio_input.getvalue()
    audio_mime = audio_input.type or "audio/wav"
    user_text = "Please understand my recorded audio and answer naturally."

# ---------------- GENERATE RESPONSE ----------------
if user_text:

    st.session_state.messages.append({
        "role": "user",
        "content": user_text if audio_bytes is None else "🎤 Audio question"
    })

    with st.chat_message("user"):
        st.markdown(
            user_text if audio_bytes is None else "🎤 Audio question received"
        )

    with st.chat_message("assistant"):

        with st.spinner("💜 JIYA is thinking..."):

            try:
                contents = []

                # Send conversation history
                for msg in st.session_state.messages:

                    if msg["role"] == "user":
                        contents.append(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part(text=msg["content"])
                                ]
                            )
                        )

                    elif msg["role"] == "assistant":
                        contents.append(
                            types.Content(
                                role="model",
                                parts=[
                                    types.Part(text=msg["content"])
                                ]
                            )
                        )

                # Add recorded audio if user used microphone
                if audio_bytes is not None:

                    contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    text="Listen to this audio, understand the question, and answer in the same language."
                                ),
                                types.Part.from_bytes(
                                    data=audio_bytes,
                                    mime_type=audio_mime
                                )
                            ]
                        )
                    )

                response = client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7
                    )
                )

                answer = response.text or "Sorry, main abhi jawab nahi de paayi."

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

                if st.session_state.voice_enabled:
                    speak_text(answer)

            except Exception as e:

                st.error(
                    "Gemini se response nahi mila. "
                    "API key, model name, internet ya quota check karo."
                )

                st.caption(str(e))
