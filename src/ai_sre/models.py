import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def get_fast_llm():
  """Fast open-weights model hosted on Groq for triage and investigation."""
  return ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.0
  )

def get_reasoning_llm():
  """Gemini 3.8 Flash for synthesis, multi-source diagnosis, and postmortem generation."""
  return ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    temperature=0.0
  )