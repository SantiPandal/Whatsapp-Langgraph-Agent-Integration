import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


def load_environment():
    """Load and validate environment variables."""
    load_dotenv()

    # Required environment variables
    required_vars = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    }

    # Check for missing variables
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    return required_vars


def setup_model(llm_config):
    """Initialize all required services."""
    # Load environment variables
    env = load_environment()

    if llm_config["provider"] == "google":
        return ChatGoogleGenerativeAI(
            model=llm_config["model"],
            temperature=llm_config["temperature"],
            google_api_key=env["GOOGLE_API_KEY"]
        )
