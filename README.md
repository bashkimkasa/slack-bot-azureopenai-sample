# slack-bot-azureopenai-sample
This is a sample slack app/bot that interacts with Azure OpenAI and Azure AI Search for RAG (Retrieval-Augmented Generation).


## Description
This is a sample python app slack app/bot that listens for incoming messages from channels the app is installed/invited in, opens a thread if not already in a thread and answer's the question if the grounding data is sufficient. It ignores all other events like message deletes for updates.
In providing an answer it makes a call to Azure OpenAI with Azure Search datasources for RAG data. It provides the search endpoint, index name and semantic configuration to use for grounding the model.
If there are additional requests from the user in the thread, it downloads all previous requests (from the user) and responses (from the bot) in the thread and adds them to the query in order to provide the model with better grounding data.
When a post from a new user in the the thread is entered that thread is considered final and the bot no longer responds to it anymore.
This is a simple app to demonstrate the functionality. It has minimal exception handling and support cases.


## Prerequisites
Please make sure that you have already created in Azure the following resources:
1. A storage account, with blob container and data files that will be used for RAG
1. An Azure OpenAI service/resource
    1. Deploy a model for LLM (example: `gpt-35-turbo-16k`)
    2. Deploy a model for text-embedding (example: `text-embedding-ada-002`)
2. An Azure (AI) Search service/resource
    1. Import and vectorize your data from above
    2. `Optional Feature` - Add custom URLs to citations.
        1. In order for citations to show an actual doc URL rather than the file path in the container follow the rest of the steps below.
        2. To the files in the container from above add a custom metadata with key `url` and for value the desired URL.
        3. To the `index` created from the import above add a custom field called `url` with same settings as the existing `title` field and save.
        4. To the `skillset` created from the import above (JSON Definition), under the `indexProjections` section, add a new object for the url using the exact same object as the `title` simply replacing the word `title` with `url` anywhere in the new object and save.
        5. In the indexer created from the import above: 
            1. `Reset` the indexer
            2. Update the indexer definition (JSON) clearing out any objects inside of the `fieldMappings`. Basically, it looks like this `"fieldMappings": []`.
            3. `Save` and `Run` the indexer.


## App Settings And Configuration 
Please create a [`slack app`](https://api.slack/com/apps) and do the following:
1. Go to `OAuth & Permissions`
    1. Go to `Scopes` section and add the `chat:write` scope to it
    2. Get the Bot User OAuth Token store somewhere for later use.
    3. At this point you can re-install the app to the workspace (but it will be done later anyway when additional scopes are added from the `Event Subscriptions`)

2. For local Development, go to `Socket Mode` and enable it.
    1. When enablig `Socket Mode`, you will get an app level token which you can give it some name to your liking.
    2. Store the app level token somewhere for later use.
    3. Leave the default app level scope as is (`connections:write`)

3. Go to `Event Subscriptions` for subscribing to specific events
    1. First turn on `Enable Events`
    2. When using `Socket Mode` (for development) above you do not need to provide a Request URL, but for production you'll need to provide the Request URL where slack will be sending the events to.

4. In `Subscribe to bot events` subscribe to the following events:
    1. `message.channels` -> A message was posted to a channel (publich) that the bot is invited in.
    2. `message.groups`   -> A message was posted to a private channel that the bot is invited in.
    3. You can add additinal optional events if needed (like message:im) for direct message with the bot.
    3. Save changes.

5. At this point you should see a warning on the top of your screen indicating to re-install the app in your workspace in order for the changes to take affect. Please go ahead and re-install the app and in the subsequent screen Allow (authorize) the new scopes.

6. Go to `App Home`
    1. Turn on the feature `Always Show My Bot as Online`
    2. If you want to change the name you can do so in the section `Your App's Presense in Slack`
    3. In the `Show Tabs` section check the box that says `Allow users to send Slash commands and messages from the messages tab`. (this setting may take a couple of minutes to propagate to slack)


## Getting started
Setup a virtual environment (optional)
```sh
python -m venv .venv
```

Activate the virtual environment (optional)
```sh
# For Linux:
source .venv/bin/activate

# For windows (gitbash etc.):
source .venv/Scripts/activate
```

Install libraries
```sh
pip install slack_bolt
pip install openai
```

Setup environment variables
```sh
# Slack Bot Variables
export SLACK_BOT_TOKEN=<fill-in-value, example: xoxb-ABC...>
export SLACK_APP_TOKEN=<fill-in-value, example: xapp-1-ABC...>

# Azure AI Variables
export AZURE_AI_ENDPOINT=<fill-in-value, example: https://my-bk-openai.openai.azure.com/>
export AZURE_AI_DEPLOYMENT=<fill-in-value, example: gpt-35-turbo-16k>
export AZURE_AI_API_KEY=<fill-in-value>
export AZURE_AI_SEARCH_ENDPOINT=<fill-in-value, example: https://my-bk-aisearch.search.windows.net>
export AZURE_AI_SEARCH_KEY=<fill-in-value>
export AZURE_AI_SEARCH_INDEX=<fill-in-value, example: vector-my-ref-data-1723475267472>
export AZURE_AI_SEARCH_SEMANTIC_CONFIGURATION=<fill-in-value, example: vector-my-ref-data-1723475267472-semantic-configuration>
```

Run python app.py file
```sh
python app.py
```
