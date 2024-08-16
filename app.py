import os
import re
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import AzureOpenAI
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Get environment variables (with defaults) TODO: Remove defaults in production
# Slack environment variables
slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
slack_app_token = os.getenv("SLACK_APP_TOKEN")

# Azure OpenAI environment variables
azure_ai_endpoint = os.getenv("AZURE_AI_ENDPOINT")
azure_ai_deployment = os.getenv("AZURE_AI_DEPLOYMENT")
azure_ai_api_key = os.getenv("AZURE_AI_API_KEY")
azure_ai_search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
azure_ai_search_key = os.getenv("AZURE_AI_SEARCH_KEY")
azure_ai_search_index = os.getenv("AZURE_AI_SEARCH_INDEX")
azure_ai_search_semantic_configuration = os.getenv("AZURE_AI_SEARCH_SEMANTIC_CONFIGURATION")

# Azure AI Search parameters customization
azure_ai_search_parameters = {
    "in_scope": False,      # Set to True to only search within the scope of the index
    "top_n_documents": 3,   # Number of documents to return in the search results
}

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=azure_ai_endpoint,
    api_key=azure_ai_api_key,
    api_version="2024-05-01-preview",
)

# Create function to call Azure OpenAI
def call_azure_openai(messages):
    completion = client.chat.completions.create(
        model=azure_ai_deployment,
        messages=messages,
        max_tokens=800,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False,
        extra_body={
            "data_sources": [{
                "type": "azure_search",
                "parameters": {
                    "endpoint": f"{azure_ai_search_endpoint}",
                    "index_name": f"{azure_ai_search_index}",
                    "semantic_configuration": f"{azure_ai_search_semantic_configuration}",
                    "query_type": "semantic",
                    "fields_mapping": {
                        "content_fields_separator": "\n",
                        "content_fields": None,
                        "filepath_field": None,
                        "title_field": "title",
                        "url_field": "url",
                        "vector_fields": [
                            "text_vector"
                        ]
                    },
                    "in_scope": azure_ai_search_parameters.get("in_scope"),
                    "role_information": "You are an AI assistant that helps people find information.",
                    "filter": None,
                    "strictness": 3,
                    "top_n_documents": azure_ai_search_parameters.get("top_n_documents"),
                    "authentication": {
                        "type": "api_key",
                        "key": f"{azure_ai_search_key}"
                    }
                }
            }]
        }
    )
    return completion.to_dict()

# Parse the response from Azure OpenAI and return content with citation hyperlinks of the top 3 search results
def parse_azure_openai_response(azure_openai_response):
    message = azure_openai_response.get("choices")[0].get("message")
    message_content = message.get("content")
    message_citations = message.get("context").get("citations")
    
    # In the message content, replace the citation references ([doc1], [docn]) with hyperlinks of the url from the citations
    citation_refs = re.findall(r"\[doc\d+\]", message_content)
    for citation_ref in citation_refs:
        citation_number = int(re.search(r"\d+", citation_ref).group())
        citation_url = message_citations[citation_number - 1].get("url")
        citation_hyperlink = f"<{citation_url}|[source-{citation_number}]>"
        message_content = message_content.replace(citation_ref, citation_hyperlink)
   
    response_message = f"{message_content}\n\n"
    return response_message


# Function to fetch all messages in a thread given the channel and thread_ts
def get_thread_messages(channel, thread_ts):
    # Get all messages in the thread
    thread_response = app.client.conversations_replies(channel=channel, ts=thread_ts)
    return thread_response["messages"]

# Function to check if another user other than the original user and the bot posted in the thread 
def external_user_added(messages):
    original_user = messages[0]["user"]
    for message in messages:
        if message["user"] != original_user and message.get("bot_id", None) is None:
            return True
    return False

# Function to add the history data to the messages list for conversation query
def add_history_to_messages(incoming_message, messages, thread_messages):
    for thread_message in thread_messages:
        if thread_message.get("bot_id", None) is not None:
            messages.append({"role": "assistant", "content": thread_message["text"]})
        # If the message from the thread is same as incoming message (or another user), skip it
        elif incoming_message["ts"] != thread_message["ts"] and incoming_message["user"] == thread_messages[0]["user"]:
            messages.append({"role": "user", "content": thread_message["text"]}) 
    
# Initializes your app with your bot token and signing secret
app = App(
    token=slack_bot_token
)

# Listens to incoming messages from channels the app is installed in
@app.message("")
def message_handler(message, say, logger):
    # Initialize the messages list for the conversation query with the system message
    messages = [{
        "role": "system",
        "content": "Answer only questions related to the topic of the conversation. Do not provide information or citations that not relevant to the conversation. Please include links from the citation content to the response message."
    }]
    logger.debug(json.dumps(message, indent=2))
    thread_ts = message.get("thread_ts", None) or message["ts"]
    ongoing_thread = "thread_ts" in message and "ts" in message
    if ongoing_thread:
        thread_messages = get_thread_messages(message["channel"], message["thread_ts"])
        logger.debug(json.dumps(thread_messages, indent=2))
        if external_user_added(thread_messages):
            logger.debug(f"Another user added to the thread. Stopping the conversation with chatbot.")
            return
        else:
            add_history_to_messages(message, messages, thread_messages)

    # Add the user's message to the messages list
    messages.append({"role": "user", "content": message["text"]})

    azure_openai_response = call_azure_openai(messages)
    logger.debug(json.dumps(azure_openai_response, indent=2))
    parsed_response = parse_azure_openai_response(azure_openai_response)
    say(f"Hi there, <@{message['user']}>\n\n{parsed_response}", thread_ts=thread_ts)

# Ignore any other event
@app.event("message")
def event_handler(event, logger):
    logger.debug(json.dumps(event, indent=2))

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, slack_app_token).start()

