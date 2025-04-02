import streamlit as st
from openai import OpenAI
import os
import time

# Pagina configuratie
st.set_page_config(page_title="Ultimo Consulancy Teams Chatbot", page_icon="💬")

# Authenticatie functie
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["app"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Wachtwoord", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error.
        st.text_input(
            "Wachtwoord", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Wachtwoord incorrect")
        return False
    else:
        # Password correct.
        return True

# Alleen tonen als het wachtwoord correct is
if check_password():
    # Titel en beschrijving
    st.title("OpenAI Assistant Chatbot")
    st.markdown("Een geavanceerde chatbot die werkt met OpenAI Assistant API")

    # Initialiseer OpenAI client met API key uit secrets
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    assistant_id = st.secrets["openai"]["assistant_id"]

    # Sidebar voor instellingen
    st.sidebar.header("Instellingen")

    # Model selectie (alleen ter informatie, we gebruiken de assistant)
    model_info = st.sidebar.info(
        "Deze chatbot gebruikt de OpenAI Assistant API met de door jou geconfigureerde assistent."
    )

    # Thread management
    if "thread_id" not in st.session_state:
        # Maak een nieuwe thread aan voor dit gesprek
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.sidebar.success(f"Nieuwe thread aangemaakt: {thread.id[:7]}...")

    st.sidebar.write(f"Huidige thread ID: {st.session_state.thread_id[:7]}...")

    # Knop om een nieuwe thread te starten
    if st.sidebar.button("Nieuwe conversatie starten"):
        # Maak een nieuwe thread aan
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        # Wis de weergegeven berichten
        st.session_state.messages = []
        st.sidebar.success(f"Nieuwe thread aangemaakt: {thread.id[:7]}...")
        st.rerun()

    # Initialiseer berichten in session state als deze nog niet bestaan
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Toon eerdere berichten
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Wat wil je weten?"):
        # Voeg gebruikersbericht toe aan UI
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Voeg het bericht toe aan de thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        # Maak een run aan met de assistant
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id
        )

        # Toon wachtbericht
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Even denken...")

            # Controleer de status van de run
            while run.status in ["queued", "in_progress"]:
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )
                time.sleep(0.5)

            # Als de run voltooid is, haal de berichten op
            if run.status == "completed":
                # Haal de berichten op van de thread
                messages = client.beta.threads.messages.list(
                    thread_id=st.session_state.thread_id
                )

                # Haal het laatste assistant bericht op
                assistant_messages = [
                    msg for msg in messages.data 
                    if msg.role == "assistant" and msg.run_id == run.id
                ]
                
                if assistant_messages:
                    latest_message = assistant_messages[0]
                    message_content = ""
                    
                    # Verwerk alle content blokken (tekst, afbeeldingen, etc.)
                    for content_block in latest_message.content:
                        if content_block.type == "text":
                            message_content += content_block.text.value
                    
                    # Update het bericht in de UI
                    message_placeholder.markdown(message_content)
                    
                    # Voeg bericht toe aan de geschiedenis
                    st.session_state.messages.append({"role": "assistant", "content": message_content})
            else:
                # Als er een fout is opgetreden
                message_placeholder.error(f"Er is een fout opgetreden: {run.status}")
                # Toon eventuele foutmeldingen
                if hasattr(run, 'last_error'):
                    st.error(f"Foutdetails: {run.last_error}")