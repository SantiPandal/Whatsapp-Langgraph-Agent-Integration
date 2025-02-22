import os

from config.logging import logger
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool, ConnectionPool
from src.callbacks import langfuse_handler


def main_test():
    try:
        checkpointer = MemorySaver()
        graph = builder.compile(checkpointer=checkpointer)

        phone_number = "31984551214"
        messages = [
            "oi",
            "Filial Vargem Grande",
            "Cupom Fiscal",
            "Entrega",
            "Tabela Entrega",
            "Boleto",
            "07 Dias",
            "Entrega | AVENIDA MP 17 VITOR EDSON MARQUES LADO NO, 12 - ALPA - BARRETOS/SP | RAIO: 50",
            "Segunda-feira, 17 de fevereiro de 2025",
            "16:00 - 23:00",
            "tudo bem e vc?",
            "quero comprar coca cola",
            "quero ver coca cola zero",
        ]
        # messages = ["oi", "Sim", "Quinta feira", "Na verdade acho que sexta fica melhor"]
        thread_id = generate_thread_id(phone_number)

        config = {
            "callbacks": [langfuse_handler],
            "configurable": {},
        }

        config["configurable"]["thread_id"] = thread_id
        config["configurable"]["phone_number"] = phone_number

        for message in messages:

            logger.info(f"Thread ID: {thread_id}")

            snapshot = graph.get_state(config)

            if not snapshot.values:
                logger.info("No snapshot found, creating new one")

                input_data = {
                    "messages": [{"role": "user", "content": message}],
                    "temp_message": "",
                    "cliente_hist_data": {},
                    "last_products_search": [],
                    "last_products_info": [],
                    "temp_data": [],
                    "order_products": [],
                    "recommendation_products": [],
                    "step": "",
                    "next_step": "",
                }

            else:
                input_data = {"messages": [{"role": "user", "content": message}]}

            if snapshot.next == ("human_review_node",) or snapshot.next == (
                "customer_input",
            ):
                for chunk in graph.stream(
                    Command(resume=input_data), config, stream_mode="updates"
                ):
                    print(chunk)
                    process_chunks(chunk, phone_number)

            else:
                for chunk in graph.stream(
                    input=input_data, config=config, stream_mode="updates"
                ):
                    print(chunk)
                    process_chunks(chunk, phone_number)
    except:
        custom_message = """Infelizmente, ocorreu um erro interno em nosso sistema. 😕 Pedimos que tente novamente mais tarde.

Se o problema persistir, entre em contato com o nosso SAC para obter suporte:

📲 Fale com nosso atendimento: https://megag.com.br/sac/

Agradecemos sua paciência e estamos à disposição para ajudá-lo! 😊✨"""
        send_message(custom_message, phone_number)
