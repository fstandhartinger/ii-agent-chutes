import json
import os
import urllib.parse
import requests
import http.client

from ii_agent.tools.base import BaseSearchClient
from ii_agent.tools.utils import truncate_content


class JinaSearchClient(BaseSearchClient):
    """
    A client for the Jina search engine.
    """

    name = "Jina"

    def __init__(self, max_results=10, **kwargs):
        self.max_results = max_results
        self.api_key = os.environ.get("JINA_API_KEY", "")

    def _search_query_by_jina(self, query, max_results=10):
        """Searches the query using Jina AI search API."""
        jina_api_key = self.api_key
        if not jina_api_key:
            print("Error: JINA_API_KEY environment variable not set")
            return []

        url = "https://s.jina.ai/"
        params = {"q": query, "num": max_results}
        encoded_url = url + "?" + urllib.parse.urlencode(params)

        headers = {
            "Authorization": f"Bearer {jina_api_key}",
            "X-Respond-With": "no-content",
            "Accept": "application/json",
        }

        search_response = []
        try:
            response = requests.get(encoded_url, headers=headers)
            if response.status_code == 200:
                search_results = response.json()["data"]
                if search_results:
                    for result in search_results:
                        search_response.append(
                            {
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "content": result.get("description", ""),
                            }
                        )
                return search_response
        except Exception as e:
            print(f"Error: {e}. Failed fetching sources. Resulting in empty response.")
            search_response = []

        return search_response

    def forward(self, query: str) -> str:
        try:
            response = self._search_query_by_jina(query, self.max_results)
            formatted_results = json.dumps(response, indent=4)
            return truncate_content(formatted_results)
        except Exception as e:
            return f"Error searching with Jina: {str(e)}"


class SerperSearchClient(BaseSearchClient):
    """
    A client for the Serper.dev search engine.
    """

    name = "Serper"

    def __init__(self, max_results=10, **kwargs):
        self.max_results = max_results
        self.api_key = os.environ.get("SERPERDEV_API_KEY", "")

    def _search_query_by_serper(self, query, max_results=10):
        """Searches the query using Serper.dev API."""
        serper_api_key = self.api_key
        if not serper_api_key:
            print("Error: SERPERDEV_API_KEY environment variable not set")
            return []

        search_response = []
        try:
            conn = http.client.HTTPSConnection("google.serper.dev")
            payload = ''
            headers = {}
            
            # URL encode the query and add API key
            encoded_query = urllib.parse.quote_plus(query)
            request_path = f"/search?q={encoded_query}&apiKey={serper_api_key}"
            
            conn.request("GET", request_path, payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            if res.status == 200:
                search_results = json.loads(data.decode("utf-8"))
                if search_results and "organic" in search_results:
                    results = search_results["organic"]
                    results_processed = 0
                    for result in results:
                        if results_processed >= max_results:
                            break
                        search_response.append(
                            {
                                "title": result.get("title", ""),
                                "url": result.get("link", ""),
                                "content": result.get("snippet", ""),
                            }
                        )
                        results_processed += 1
            conn.close()
        except Exception as e:
            print(f"Error: {e}. Failed fetching sources. Resulting in empty response.")
            search_response = []

        return search_response

    def forward(self, query: str) -> str:
        try:
            response = self._search_query_by_serper(query, self.max_results)
            formatted_results = json.dumps(response, indent=4)
            return truncate_content(formatted_results)
        except Exception as e:
            return f"Error searching with Serper: {str(e)}"


class DuckDuckGoSearchClient(BaseSearchClient):
    """
    A client for the DuckDuckGo search engine.
    """

    name = "DuckDuckGo"

    def __init__(self, max_results=10, **kwargs):
        self.max_results = max_results
        try:
            from duckduckgo_search import DDGS
        except ImportError as e:
            raise ImportError(
                "You must install package `duckduckgo-search` to run this tool: for instance run `pip install duckduckgo-search`."
            ) from e
        self.ddgs = DDGS(**kwargs)

    def forward(self, query: str) -> str:
        results = self.ddgs.text(query, max_results=self.max_results)
        if len(results) == 0:
            raise Exception("No results found! Try a less restrictive/shorter query.")
        postprocessed_results = [
            f"[{result['title']}]({result['href']})\n{result['body']}"
            for result in results
        ]
        return truncate_content(
            "## Search Results\n\n" + "\n\n".join(postprocessed_results)
        )


class TavilySearchClient(BaseSearchClient):
    """
    A client for the Tavily search engine.
    """

    name = "Tavily"

    def __init__(self, max_results=5, **kwargs):
        self.max_results = max_results
        self.api_key = os.environ.get("TAVILY_API_KEY", "")
        if not self.api_key:
            print(
                "Warning: TAVILY_API_KEY environment variable not set. Tool may not function correctly."
            )

    def forward(self, query: str) -> str:
        try:
            from tavily import TavilyClient
        except ImportError as e:
            raise ImportError(
                "You must install package `tavily` to run this tool: for instance run `pip install tavily-python`."
            ) from e

        try:
            # Initialize Tavily client
            tavily_client = TavilyClient(api_key=self.api_key)

            # Perform search
            response = tavily_client.search(query=query, max_results=self.max_results)

            # Check if response contains results
            if not response or "results" not in response or not response["results"]:
                return f"No search results found for query: {query}"

            # Format and return the results
            formatted_results = json.dumps(response["results"], indent=4)
            return truncate_content(formatted_results)

        except Exception as e:
            return f"Error searching with Tavily: {str(e)}"


class ImageSearchClient:
    """
    A client for the Serper.dev image search engine.
    """

    name = "SerperImages"

    def __init__(self, max_results=10, **kwargs):
        self.max_results = max_results
        self.api_key = os.environ.get("SERPERDEV_API_KEY", "")

    def _search_query_by_serper_images(self, query, max_results=10):
        """Searches for images using Serper.dev API."""
        serper_api_key = self.api_key
        if not serper_api_key:
            print("Error: SERPERDEV_API_KEY environment variable not set")
            return []

        search_response = []
        try:
            conn = http.client.HTTPSConnection("google.serper.dev")
            payload = ''
            headers = {}
            
            # URL encode the query and add API key, specify images search
            encoded_query = urllib.parse.quote_plus(query)
            request_path = f"/images?q={encoded_query}&apiKey={serper_api_key}"
            
            conn.request("GET", request_path, payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            if res.status == 200:
                search_results = json.loads(data.decode("utf-8"))
                if search_results and "images" in search_results:
                    results = search_results["images"]
                    results_processed = 0
                    for result in results:
                        if results_processed >= max_results:
                            break
                        search_response.append(
                            {
                                "title": result.get("title", ""),
                                "image_url": result.get("imageUrl", ""),
                                "width": result.get("imageWidth", 0),
                                "height": result.get("imageHeight", 0),
                            }
                        )
                        results_processed += 1
            conn.close()
        except Exception as e:
            print(f"Error: {e}. Failed fetching sources. Resulting in empty response.")
            search_response = []

        return search_response

    def forward(self, query: str) -> str:
        try:
            response = self._search_query_by_serper_images(query, self.max_results)
            formatted_results = json.dumps(response, indent=4)
            return truncate_content(formatted_results)
        except Exception as e:
            return f"Error searching with Serper Images: {str(e)}"


def create_search_client(max_results=10, **kwargs) -> BaseSearchClient:
    """
    A search client that selects from available search APIs in the following order:
    Tavily > Jina > Serper > DuckDuckGo

    It defaults to DuckDuckGo if no API keys are found for the other services.
    """

    serper_api_key = os.environ.get("SERPERDEV_API_KEY", "")
    if serper_api_key:
        print("Using Serper.dev to search")
        return SerperSearchClient(max_results=max_results, **kwargs)

    jina_api_key = os.environ.get("JINA_API_KEY", "")
    if jina_api_key:
        print("Using Jina to search")
        return JinaSearchClient(max_results=max_results, **kwargs)

    tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
    if tavily_api_key:
        print("Using Tavily to search")
        return TavilySearchClient(max_results=max_results, **kwargs)

    print("Using DuckDuckGo to search")
    return DuckDuckGoSearchClient(max_results=max_results, **kwargs)


def create_image_search_client(max_results=5, **kwargs) -> ImageSearchClient:
    """
    A search client that selects from available image search APIs.
    Uses Serper.dev for image search if API key is available.
    """
    if os.environ.get("SERPERDEV_API_KEY"):
        print("Using Serper.dev to search for images")
        return ImageSearchClient(max_results=max_results, **kwargs)
    else:
        print("No image search API key found, using DuckDuckGo")
        return None
