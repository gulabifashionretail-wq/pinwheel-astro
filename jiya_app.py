
import streamlit as st
import streamlit.components.v1 as components
import hashlib
import json
import time

from google import genai
from google.genai import types


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="JIYA Personal AI",
    page_icon="💗",
    layout="centered"
)


# =========================================================
# JIYA DESIGN
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #fff7fb, #fce8f2);
    }

    .jiya-title {
        text-align: center;
        color: #c2185b;
        font-size: 38px;
        font-weight: 800;
    }

    .jiya-subtitle {
        text-align: center;
        color: #795568;
        font-size: 15px;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 15px;
    }

    .stButton button {
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<div class="jiya-title">💗 JIYA AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="jiya-subtitle">'
    'Your friendly personal AI assistant'
    '</div>',
    unsafe_allow_html=True
)

st.write("")


# =========================================================
# SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

if "last_request_hash" not in st.session_state:
    st.session_state.last_request_hash = None

if "last_answer" not in st.session_state:
    st.session_state.last_answer = ""

if "last_answer_id" not in st.session_state:
    st.session_state.last_answer_id = 0

if "last_speech_id" not in st.session_state:
    st.session_state.last_speech_id = -1

if "pending_speech" not in st.session_state:
    st.session_state.pending_speech = None


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("⚙️ JIYA Settings")

    st.caption("Gemini AI")

    model_name = st.text_input(
        "Gemini Model ID",
        value="gemini-3.8-flash",
        help=(
            "Use the exact model ID available for your API key. "
            "If this model gives 404, select an available Flash model."
        )
    ).strip()

    speak_replies = st.checkbox(
        "Speak AI replies",
        value=True,
        key="speak_replies"
    )

    st.caption(
        "Voice depends on the voices installed in your browser/device."
    )

    st.divider()

    if st.button("🛑 Stop Speaking", use_container_width=True):

        components.html(
            """
            <script>
            window.speechSynthesis.cancel();
            </script>
            """,
            height=0
        )

    if st.button("🗑️ Clear Chat", use_container_width=True):

        st.session_state.messages = []
        st.session_state.last_audio_hash = None
        st.session_state.last_request_hash = None
        st.session_state.last_answer = ""
        st.session_state.last_answer_id = 0
        st.session_state.last_speech_id = -1
        st.session_state.pending_speech = None

        st.rerun()

    st.divider()

    st.caption("JIYA AI • Gemini-powered assistant")


# =========================================================
# API KEY
# =========================================================

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]

except Exception:

    st.error(
        "Gemini API key missing. Add GEMINI_API_KEY "
        "inside Streamlit Cloud Secrets."
    )

    st.stop()


if not API_KEY:

    st.error("GEMINI_API_KEY is empty.")

    st.stop()


# =========================================================
# GEMINI CLIENT
# =========================================================

@st.cache_resource
def create_gemini_client(api_key):

    return genai.Client(
        api_key=api_key
    )


try:

    client = create_gemini_client(API_KEY)

except Exception as error:

    st.error(f"Gemini client initialization failed: {error}")

    st.stop()


# =========================================================
# JIYA PERSONALITY
# =========================================================

SYSTEM_PROMPT = """
You are JIYA, a friendly and intelligent personal AI assistant.

PERSONALITY:
- Friendly, polite, caring, calm and helpful.
- Speak naturally like a helpful human assistant.
- Use Hindi, Hinglish or English based on the user's language.
- If the user says HI, HELLO, NAMASTE or asks a simple question,
  reply immediately with a short natural answer.
- Do not give unnecessarily long replies.
- Keep simple answers short.
- Explain difficult topics in easy language.
- Help with CDS preparation, English grammar, GK, coding,
  learning and daily questions.
- Do not repeat the user's question unnecessarily.
- Do not claim to be a real human.
- Do not claim that you have performed actions you did not perform.
- If the user asks for something unclear, ask one short question.
- Prefer a direct useful answer over unnecessary introductions.
"""


# =========================================================
# CHAT DISPLAY
# =========================================================

for message in st.session_state.messages:

    role = message["role"]

    content = message["content"]

    if role == "user":

        with st.chat_message("user"):

            st.markdown(content)

    elif role == "assistant":

        with st.chat_message("assistant"):

            st.markdown(content)


# =========================================================
# RESPONSE VOICE
# =========================================================

def speak_text(text, speech_id):

    # Do not speak the same response more than once.
    if speech_id == st.session_state.last_speech_id:

        return

    st.session_state.last_speech_id = speech_id

    # Safely pass text to JavaScript.
    safe_text = json.dumps(
        text,
        ensure_ascii=False
    )

    components.html(
        f"""
        <script>
        const text = {safe_text};

        if ("speechSynthesis" in window) {{

            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);

            const voices = window.speechSynthesis.getVoices();

            let selectedVoice = null;

            const preferredNames = [
                "Heera",
                "Veena",
                "Priya",
                "Google हिन्दी",
                "Google Hindi",
                "Microsoft Heera",
                "Microsoft Veena"
            ];

            for (const preferred of preferredNames) {{

                selectedVoice = voices.find(
                    voice => voice.name.toLowerCase().includes(
                        preferred.toLowerCase()
                    )
                );

                if (selectedVoice) break;
            }}

            if (!selectedVoice) {{

                selectedVoice = voices.find(
                    voice => voice.lang.toLowerCase().startsWith("hi")
                );
            }}

            if (!selectedVoice) {{

                selectedVoice = voices.find(
                    voice => voice.lang.toLowerCase().startsWith("en-in")
                );
            }}

            if (selectedVoice) {{
                utterance.voice = selectedVoice;
            }}

            utterance.rate = 0.92;
            utterance.pitch = 1.05;
            utterance.volume = 1;

            window.speechSynthesis.speak(utterance);
        }}
        </script>
        """,
        height=0
    )


# =========================================================
# AUDIO INPUT
# =========================================================

st.markdown("### 🎤 Ask JIYA")

audio_file = st.audio_input(
    "Record your question",
    key="jiya_audio_input"
)


# =========================================================
# TEXT INPUT
# =========================================================

text_prompt = st.chat_input(
    "Message JIYA..."
)


# =========================================================
# REQUEST PROCESSING
# =========================================================

current_prompt = None

current_audio_bytes = None

current_audio_mime = None

request_source = None


# Text takes priority if both are provided.
if text_prompt:

    current_prompt = text_prompt.strip()

    request_source = "text"


elif audio_file is not None:

    try:

        audio_bytes = audio_file.getvalue()

        if audio_bytes:

            audio_hash = hashlib.sha256(
                audio_bytes
            ).hexdigest()

            if audio_hash != st.session_state.last_audio_hash:

                st.session_state.last_audio_hash = audio_hash

                current_audio_bytes = audio_bytes

                current_audio_mime = (
                    audio_file.type or "audio/wav"
                )

                current_prompt = (
                    "Listen to the user's audio. "
                    "Understand the spoken question and answer it. "
                    "If it is Hindi or Hinglish, respond naturally "
                    "in Hindi or Hinglish. "
                    "If the audio is unclear, ask the user to repeat."
                )

                request_source = "audio"

    except Exception as audio_error:

        st.error(
            f"Microphone input error: {audio_error}"
        )


# =========================================================
# SEND REQUEST
# =========================================================

if current_prompt and request_source:

    request_id = hashlib.sha256(
        (
            request_source
            + current_prompt
            + (
                hashlib.sha256(
                    current_audio_bytes
                ).hexdigest()
                if current_audio_bytes
                else ""
            )
        ).encode("utf-8")
    ).hexdigest()

    # Prevent duplicate request.
    if request_id == st.session_state.last_request_hash:

        st.info("This message has already been processed.")

    else:

        st.session_state.last_request_hash = request_id

        # Display audio questions as a simple label.
        if request_source == "audio":

            display_prompt = "🎤 Voice question"

        else:

            display_prompt = current_prompt

        # Save user message once.
        st.session_state.messages.append(
            {
                "role": "user",
                "content": display_prompt
            }
        )

        with st.chat_message("user"):

            st.markdown(display_prompt)

        # Build conversation history.
        contents = []

        for message in st.session_state.messages[:-1]:

            if message["role"] == "user":

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(
                                text=message["content"]
                            )
                        ]
                    )
                )

            elif message["role"] == "assistant":

                contents.append(
                    types.Content(
                        role="model",
                        parts=[
                            types.Part.from_text(
                                text=message["content"]
                            )
                        ]
                    )
                )

        # Build current message.
        current_parts = []

        if request_source == "text":

            current_parts.append(
                types.Part.from_text(
                    text=current_prompt
                )
            )

        elif request_source == "audio":

            current_parts.append(
                types.Part.from_text(
                    text=current_prompt
                )
            )

            current_parts.append(
                types.Part.from_bytes(
                    data=current_audio_bytes,
                    mime_type=current_audio_mime
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=current_parts
            )
        )

        # Gemini request.
        with st.chat_message("assistant"):

            response_placeholder = st.empty()

            try:

                with st.spinner("JIYA is thinking..."):

                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.5,
                            max_output_tokens=300
                        )
                    )

                ai_reply = response.text

                if not ai_reply:

                    ai_reply = (
                        "Sorry, mujhe response nahi mila. "
                        "Please ek baar phir try karein."
                    )

                response_placeholder.markdown(
                    ai_reply
                )

                # Save assistant response exactly once.
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": ai_reply
                    }
                )

                st.session_state.last_answer = ai_reply

                st.session_state.last_answer_id += 1

                st.session_state.pending_speech = (
                    ai_reply,
                    st.session_state.last_answer_id
                )

            except Exception as api_error:

                error_text = str(api_error)

                if (
                    "404" in error_text
                    or "NOT_FOUND" in error_text.upper()
                ):

                    st.error(
                        "Gemini model unavailable (404). "
                        "Sidebar mein available model ka exact ID "
                        "select karein. API key change karna zaroori "
                        "nahi hai."
                    )

                elif (
                    "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text.upper()
                ):

                    st.error(
                        "Gemini quota ya rate limit reached. "
                        "Thodi der baad try karein."
                    )

                elif (
                    "401" in error_text
                    or "403" in error_text
                    or "PERMISSION_DENIED" in error_text.upper()
                ):

                    st.error(
                        "API key invalid, restricted, or missing "
                        "permission. Check your Google AI Studio key."
                    )

                else:

                    st.error(
                        "JIYA could not get a reply. "
                        "Please check internet/API settings and try again."
                    )

                st.caption(error_text[:500])


# =========================================================
# SPEAK REPLY CONTROL
# =========================================================

if st.session_state.last_answer:

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🔊 Speak Reply",
            use_container_width=True
        ):

            speak_text(
                st.session_state.last_answer,
                st.session_state.last_answer_id
            )

    with col2:

        if st.button(
            "🛑 Stop Voice",
            use_container_width=True
        ):

            components.html(
                """
                <script>
                window.speechSynthesis.cancel();
                </script>
                """,
                height=0
            )


# =========================================================
# AUTO SPEAK NEW REPLY
# =========================================================

if (
    speak_replies
    and st.session_state.pending_speech is not None
):

    pending_text, pending_id = (
        st.session_state.pending_speech
    )

    if pending_id != st.session_state.last_speech_id:

        speak_text(
            pending_text,
            pending_id
        )

    st.session_state.pending_speech = None
