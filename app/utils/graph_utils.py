import os
import tempfile
import uuid

from dotenv import load_dotenv
from gtts import gTTS
from IPython.display import Image
from langchain_core.messages import AIMessage
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from langgraph.graph import StateGraph
from rich.console import Console

from app.src.wppconnect.api import send_voice

rich = Console()

load_dotenv()

LANG = os.getenv("LANG", "en")


def print_graph(graph: StateGraph, image_name: str = "graph.png") -> None:
    """
    Create a mermaid graph

    args:
        graph (StateGraph): the graph
        image_name (str): file name
    """
    Image(
        graph.get_graph().draw_mermaid_png(
            curve_style=CurveStyle.LINEAR,
            node_colors=NodeStyles(first="#ffdfba", last="#baffc9", default="#fad7de"),
            wrap_label_n_words=9,
            output_file_path=image_name,
            draw_method=MermaidDrawMethod.PYPPETEER,
            background_color="white",
            padding=10,
        )
    )


def generate_thread_id(user_id: str) -> str:
    """Generates a deterministic thread ID based on the user ID."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"thread-{user_id}"))


def process_chunks(chunk, phone_number):
    """
    Processes a chunk from the agent and displays information about tool calls or the agent's answer.

    Parameters:
        chunk (dict): A dictionary containing information about the agent's messages.

    Returns:
        None

    This function processes a chunk of data to check for agent messages.
    It iterates over the messages and checks for tool calls.
    If a tool call is found, it extracts the tool name and query, then prints a formatted message using the Rich library.
    If no tool call is found, it extracts and prints the agent's answer using the Rich library.
    """
    if isinstance(chunk, dict):
        if "messages" in chunk[list(chunk.keys())[0]]:
            message = chunk[list(chunk.keys())[0]]["messages"]

            if isinstance(message, AIMessage):
                agent_answer = message.content
                if isinstance(agent_answer, list):
                    for answer in agent_answer:
                        rich.print(f"\nAgent:\n{answer}", style="black on white")

                if isinstance(agent_answer, str):
                    agent_answer = message.content
                    rich.print(
                        f"\nAgent:\n{agent_answer}",
                        style="black on white",
                    )

                    print("LAAAANG: ", LANG)
                    tts = gTTS(text=agent_answer, lang=LANG)

                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".mp3"
                    ) as temp_audio:
                        audio_path = temp_audio.name
                        tts.save(audio_path)

                    send_voice(audio_path, phone_number)
