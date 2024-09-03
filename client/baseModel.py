from langchain_openai import ChatOpenAI


class my_model(ChatOpenAI):
    def get_num_tokens_from_messages(self, text):
        return 1000

