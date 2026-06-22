"""HTTP client for the word-api and hanzi-api endpoints."""
import urllib.parse
from typing import Dict, List, Optional

import requests


class WordApiClient:
    DEFAULT_BASE_URL = "http://localhost:7998"

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5):
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout

    def _quote(self, term: str) -> str:
        return urllib.parse.quote(term, safe='')

    def fetch_word_info(self, word: str) -> Optional[Dict]:
        url = f"{self.base_url}/word-api/{self._quote(word)}"
        print(f"Fetching word info for: {word} from {url}")
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 'unknown'
            body = e.response.text[:200] if e.response is not None else ''
            print(f"HTTPError em word-api para {word} — status {status}; corpo: {body}")
            return None
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Error fetching data for word {word}: {e}")
            return None

    def search(self, query: str) -> List[Dict]:
        """Search words by character, pinyin or translation term."""
        url = f"{self.base_url}/word-api/search?q={self._quote(query)}"
        print(f"Searching words for: {query} from {url}")
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Error searching for {query}: {e}")
            return []

    def fetch_character_info(self, character: str) -> Optional[Dict]:
        encoded = self._quote(character)
        url = f"{self.base_url}/hanzi-api/hanzi/{encoded}"
        print(f"Fetching character info for: {character} from {url}")
        try:
            r = requests.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()

            if not data.get('meaning') or not data.get('decomposition'):
                print(f"Character {character} needs enrichment - calling enrich endpoint")
                try:
                    enrich_url = f"{self.base_url}/hanzi-api/hanzi/{encoded}/enrich"
                    requests.put(enrich_url, timeout=10).raise_for_status()
                    r2 = requests.get(url, timeout=self.timeout)
                    r2.raise_for_status()
                    data = r2.json()
                    print(f"Updated API response for {character}: {data}")
                except requests.exceptions.RequestException as e:
                    print(f"Error enriching character {character}: {e}")
            return data
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Error fetching data for character {character}: {e}")
            return None
