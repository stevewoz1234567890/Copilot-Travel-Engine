import pickle
from tavily import TavilyClient
from API_KEYS import TAVILY_API_KEY

# web search using travily api
def simple_web_search(query):
    client = TavilyClient(api_key=TAVILY_API_KEY)

    content  = client.search(query=query, search_depth="advanced")
    print("Save url info as pickle file.")
    with open('langgraph_doc_url.pickle', 'wb') as f:
        pickle.dump(content, f)

    return content