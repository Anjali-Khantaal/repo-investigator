from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BACKEND_URL = os.getenv('BACKEND_PUBLIC_URL', 'http://localhost:8001').rstrip('/')

st.set_page_config(page_title='repo-investigator', layout='wide')
st.title('repo-investigator')
st.caption('A codebase investigation agent for learning DSPy, MLflow tracing, and optional NeMo orchestration.')


def _get(path: str) -> tuple[Any | None, str | None]:
    try:
        response = requests.get(f'{BACKEND_URL}{path}', timeout=30)
        response.raise_for_status()
        return response.json(), None
    except Exception as exc:
        return None, str(exc)


def _post(path: str, payload: dict[str, Any]) -> tuple[Any | None, str | None]:
    try:
        response = requests.post(f'{BACKEND_URL}{path}', json=payload, timeout=120)
        response.raise_for_status()
        return response.json(), None
    except Exception as exc:
        return None, str(exc)


if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_response' not in st.session_state:
    st.session_state.last_response = None

health, health_error = _get('/health')

with st.sidebar:
    st.subheader('Connection')
    st.write(f'Backend: `{BACKEND_URL}`')
    if health_error:
        st.error(health_error)
    else:
        st.success(f"Connected in {health['effective_mode']} mode")
        if health.get('warnings'):
            for warning in health['warnings']:
                st.warning(warning)

    st.subheader('Repository')
    known_repo_options = []
    if health and health.get('known_repos'):
        known_repo_options = [item['path'] for item in health['known_repos']]

    default_repo = health['default_repo'] if health else ''
    repo_path = st.selectbox('Known repos', options=known_repo_options or [default_repo], index=0 if known_repo_options else None)
    custom_repo_path = st.text_input('Or enter a custom path', value=repo_path)
    developer_mode = st.checkbox('Developer mode', value=True)

    st.subheader('Starter prompts')
    starter_prompts = [
        'Where is authentication handled?',
        'Trace the user listing flow.',
        'Which files would likely change to add rate limiting?',
        'Summarize the token logic.',
    ]
    for prompt in starter_prompts:
        if st.button(prompt):
            st.session_state.prefill_prompt = prompt

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

prompt = st.chat_input('Ask about the selected repository...')
if not prompt and st.session_state.get('prefill_prompt'):
    prompt = st.session_state.pop('prefill_prompt')

if prompt:
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)

    payload = {
        'question': prompt,
        'repo_path': custom_repo_path or repo_path,
        'developer_mode': developer_mode,
    }
    with st.chat_message('assistant'):
        with st.spinner('Investigating the repository...'):
            result, error = _post('/ask', payload)
        if error:
            st.error(error)
            st.session_state.messages.append({'role': 'assistant', 'content': f'Error: {error}'})
        else:
            st.markdown(result['answer'])
            st.caption(f"Mode: {result['mode']} • Latency: {result['latency_ms']} ms • Run ID: {result['run_id']}")
            st.session_state.messages.append({'role': 'assistant', 'content': result['answer']})
            st.session_state.last_response = result

last = st.session_state.get('last_response')
if last:
    st.divider()
    col1, col2 = st.columns([1.1, 1.0])

    with col1:
        st.subheader('Citations')
        for citation in last.get('citations', []):
            with st.expander(citation['file_path'], expanded=False):
                st.write(citation['reason'])

        st.subheader('Evidence')
        for item in last.get('evidence', []):
            with st.expander(f"{item['file_path']}  • score={item['score']}", expanded=False):
                st.write(item['summary'])
                st.code(item['snippet'])

    with col2:
        st.subheader('Developer panel')
        if last.get('warnings'):
            for warning in last['warnings']:
                st.warning(warning)

        for step in last.get('steps', []):
            with st.expander(step['stage'], expanded=False):
                st.write(step['summary'])
                st.json(step['details'])
