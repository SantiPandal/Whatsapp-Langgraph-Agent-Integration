import os
from typing import Annotated

from config.config import setup_model
from config.logging import logger
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from src.wppconnect.api import send_message
from typing_extensions import TypedDict
from utils.graph_utils import generate_thread_id, process_chunks

# Initialize dotenv to load environment variables
load_dotenv()


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


llm_config = {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.6}
llm_model = setup_model(llm_config)

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable


class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State):
        while True:
            result = self.runnable.invoke(state)
            if (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você é a Dra. Sofia, uma terapeuta compassiva e empática."
            "Seu objetivo é fornecer orientação de apoio, sem julgamentos, e ajudar os usuários "
            "a explorar suas emoções e pensamentos.",
        ),
        ("placeholder", "{messages}"),
    ]
)


assistant_runnable = primary_assistant_prompt | llm_model


builder = StateGraph(State)


# Define nodes: these do the work
builder.add_node("assistant", Assistant(assistant_runnable))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)


async def main(phone_number, message):
    try:
        async with AsyncConnectionPool(
            conninfo=os.getenv("PSQL_CONNECTION_STRING"),
            max_size=20,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        ) as pool, pool.connection() as conn:
            checkpointer = AsyncPostgresSaver(conn)

            #await checkpointer.setup() # FIRST EXECUTION ONLY

            graph = builder.compile(checkpointer=checkpointer)

            thread_id = generate_thread_id(phone_number)

            config = {
                "configurable": {},
            }

            config["configurable"]["thread_id"] = thread_id
            config["configurable"]["phone_number"] = phone_number

            logger.info(f"Thread ID: {thread_id}")

            input_data = {"messages": [{"role": "user", "content": message}]}

            async for chunk in graph.astream(
                input=input_data, config=config, stream_mode="updates"
            ):
                print(chunk)
                process_chunks(chunk, phone_number)
    except:
        custom_message = """Infelizmente, ocorreu um erro interno em nosso sistema. 😕 Pedimos que tente novamente mais tarde."""
        send_message(custom_message, phone_number)
