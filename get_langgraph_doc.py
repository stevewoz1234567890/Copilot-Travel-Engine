from langchain_community.document_loaders import GitHubIssuesLoader, GithubFileLoader, SeleniumURLLoader
import nbformat
from nbconvert import PythonExporter
import os

from API_KEYS import ACCESS_TOKEN

# get issues from github repo
def load_issue_github(repo="langchain-ai/langgraph", token=ACCESS_TOKEN):
    print('load issues from github repo "' + repo + '"')
    loader = GitHubIssuesLoader(
        repo=repo,
        access_token=token, 
    )
    docs = loader.load()
    concatenated_content = "\n\n\n --- \n\n\n".join(
        [doc.page_content for doc in docs]
    )
    return concatenated_content

# get source codes from github repo
def load_code_github(repo="langchain-ai/langgraph", 
                     token=ACCESS_TOKEN,
                     file_type=".md"):
    print('load codes from github repo "' + repo + '"')
    if file_type == ".md":
        loader = GithubFileLoader(
            repo=repo,  # the repo name
            access_token=ACCESS_TOKEN,
            github_api_url="https://api.github.com",
            file_filter=lambda file_path: file_path.endswith(".md"), 
        )
        documents = loader.load()
        concatenated_content = "\n\n\n --- \n\n\n".join(
            [doc.page_content for doc in documents]
        )
        return concatenated_content 
       
    elif file_type == ".ipynb":
        loader = GithubFileLoader(
            repo=repo,  # the repo name
            access_token=ACCESS_TOKEN,
            github_api_url="https://api.github.com",
            file_filter=lambda file_path: file_path.endswith(".ipynb"), 
        )
        documents = loader.load()

        # ipynb file to txt file
        exporter = PythonExporter()
        scripts = []
        for _ in documents:
            notebook = nbformat.reads(_.page_content, as_version=4)
            python_script, _ = exporter.from_notebook_node(notebook)
            scripts.append(python_script)
        
        concatenated_content = "\n\n\n --- \n\n\n".join(
            [doc for doc in scripts]
        )
        return concatenated_content 

def load_doc_url(urls=["https://python.langchain.com/docs/langgraph"]):
    
    print('load documents from urls: "')
    for _ in urls:
        print(_)

    loader = SeleniumURLLoader(urls=urls)
    data = loader.load()
    concatenated_content = "\n\n\n --- \n\n\n".join(
        [doc.page_content for doc in data]
    )
    return concatenated_content

# Sort the list based on the URLs in 'metadata' -> 'source'
def sorted_by_url(docs, key="source"):
    d_sorted = sorted(docs, key=lambda x: x.metadata[key])
    d_reversed = list(reversed(d_sorted))
    return d_reversed

def get_all_docs():
    all_docs = []

    # docs = load_issue_github()
    # all_docs.append(docs)

    docs = load_doc_url()
    all_docs.append(docs)

    docs = load_code_github(file_type='.md')
    all_docs.append(docs)

    docs = load_code_github(file_type='.ipynb')
    all_docs.append(docs)

    concatenated_content = "\n\n\n --- \n\n\n".join(
        [doc for doc in all_docs]
    )

    return concatenated_content

def load_docs(path='./langgraph_doc.txt'):
    if os.path.exists(path):
        print("The doc path exists.")
        print("Load docs from local file.")
        with open(path, encoding='utf-8') as f:
            docs = f.read()
            return docs
    else:
        print("The doc path does not exist.")
        docs = get_all_docs()
        print("Save docs as txt file.")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(docs)
        return docs

# load_docs()