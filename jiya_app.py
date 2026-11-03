import os
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="JIYA AI", page_icon="🤖", layout="wide")

# Configure OPENAI_API_KEY in Streamlit Secrets or environment variables.
api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
if not api_key:
    st.warning("Add OPENAI_API_KEY in Streamlit → App settings → Secrets to enable JIYA's AI.")
    st.code('OPENAI_API_KEY = "your_api_key_here"', language="toml")
    st.stop()

client = OpenAI(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": (
            "You are JIYA, a helpful personal AI assistant with a warm, friendly, "
            "feminine-presenting voice/personality. Speak naturally. Use Hindi or Hinglish "
            "when the user does, and English when they do. Be honest about your capabilities. "
            "Never claim to control or connect devices unless an integration actually exists."
        )}
    ]

st.markdown("""
<style>
.stApp { background: radial-gradient(ellipse at top, #1b1640 0%, #0b1020 45%, #080b14 100%); }
[data-testid="stHeader"] { background: transparent; }
.jiya-title { font-size: 3rem; font-weight: 800; letter-spacing: .04em; color: #f4eaff; }
.jiya-sub { color: #c7c3e8; font-size: 1.05rem; }
div[data-testid="stChatMessage"] { border: 1px solid rgba(183,155,255,.16); border-radius: 16px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ JIYA Settings")
    model = st.selectbox("AI model", ["gpt-4o-mini", "gpt-4.1-mini"], index=0)
    voice = st.selectbox("Voice", ["shimmer", "nova", "alloy", "coral"], index=0)
    speak = st.toggle("Speak replies", value=True)
    st.caption("Voice availability and pronunciation depend on the selected speech model.")
    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()
    st.caption("Cross-device use: open this same deployed app URL on your other devices. "
               "Conversation sync requires a database/login integration.")

st.markdown('<div class="jiya-title">✨ JIYA AI</div>', unsafe_allow_html=True)
st.markdown('<div class="jiya-sub">Your personal AI • Voice • Hindi / Hinglish / English</div>', unsafe_allow_html=True)
st.divider()

for msg in st.session_state.messages[1:]:
    with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
        st.markdown(msg["content"])

# Voice input (supported by current Streamlit versions)
audio = st.audio_input("🎙️ Speak to JIYA", key="voice_input")
if audio is not None:
    if st.session_state.get("last_audio_bytes") != audio.getvalue():
        st.session_state.last_audio_bytes = audio.getvalue()
        with st.spinner("JIYA is listening..."):
            try:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("voice_input.wav", audio.getvalue(), "audio/wav")
                )
                spoken_text = transcript.text.strip()
                if spoken_text:
                    st.session_state.pending_voice_text = spoken_text
                    st.success(f"You said: {spoken_text}")
            except Exception as e:
                st.error(f"Voice transcription failed: {e}")

prompt = st.chat_input("Message JIYA...")
pending_voice = st.session_state.pop("pending_voice_text", None)
user_text = prompt or pending_voice

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("JIYA is thinking..."):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=st.session_state.messages,
                    temperature=0.7
                )
                answer = response.choices[0].message.content or "I couldn't create a response."
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

                if speak:
                    try:
                        audio_response = client.audio.speech.create(
                            model="tts-1",
                            voice=voice,
                            input=answer
                        )
                        audio_bytes = audio_response.read()
                        st.audio(audio_bytes, format="audio/mpeg", autoplay=True)
                    except Exception as e:
                        st.info(f"Text reply is ready; speech could not be generated: {e}")
            except Exception as e:
                st.error(f"JIYA could not connect to the AI service: {e}")

st.caption("Prototype: chat history is stored in this browser session only. Add authentication and a database for persistent cross-device memory.")

