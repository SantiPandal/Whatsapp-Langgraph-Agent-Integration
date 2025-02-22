import os
from typing import Annotated

from config.config import setup_model
from config.logging import logger
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import create_react_agent
from src.wppconnect.api import send_message
from typing_extensions import TypedDict
from utils.graph_utils import generate_thread_id, process_chunks

# Initialize dotenv to load environment variables
load_dotenv()


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


llm_config = {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.6}


llm_model = setup_model(llm_config)


def main(message, phone_number):
    try:
        checkpointer = MemorySaver()

        graph = create_react_agent(
            llm_model, checkpointer=checkpointer, state_schema=State
        )

        thread_id = generate_thread_id(phone_number)

        config = {
            "configurable": {},
        }

        config["configurable"]["thread_id"] = thread_id
        config["configurable"]["phone_number"] = phone_number

        logger.info(f"Thread ID: {thread_id}")

        input_data = {"messages": [{"role": "user", "content": message}]}

        for chunk in graph.stream(
            input=input_data, config=config, stream_mode="updates"
        ):
            print(chunk)
            process_chunks(chunk, phone_number)
    except:
        custom_message = """Infelizmente, ocorreu um erro interno em nosso sistema. 😕 Pedimos que tente novamente mais tarde."""
        send_message(custom_message, phone_number)
