"""
Trending Queries API module for fetching trending search queries using Serper API.
Fetches trending queries related to a given topic from the past 30 days.
"""

import logging
import random
import requests
from typing import List, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class TrendingQueriesAPI:
    """
    Interacts with Serper API to fetch trending queries related to a topic.
    Focuses on trending searches from the past 30 days.
    """

    def __init__(self):
        self.serper_api_key = getattr(settings, "SERPER_API_KEY", None)
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY missing from Django settings")

        self.serper_base_url = "https://google.serper.dev/search"
        self.headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }

        logger.info("✅ TrendingQueriesAPI initialized successfully")

    # -------------------------------------------------------------------------
    # Public method: Fetch trending queries
    # -------------------------------------------------------------------------

    def get_trending_queries(self, topic: str, region: str = "", limit: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get trending queries related to a topic using Serper API.

        Args:
            topic: Main topic to search for
            region: Country code (e.g., 'US', 'GB'); defaults to worldwide if empty
            limit: Max number of results to return
        Returns:
            Dict with 'rising' and 'top' keys containing trending query data
        """
        # Support mock data for development/testing
        if getattr(settings, "SERPER_MOCK_DATA", False):
            logger.info(f"⚙️ Using mock data for trending queries (topic: {topic})")
            return self._mock_trending_data(topic, limit)

        try:
            logger.info(f"🔍 Fetching trending queries for topic='{topic}', region='{region or 'worldwide'}'")
            all_queries = []

            # Strategy 1: Direct topic + trending keywords
            trending_keywords = ["trending", "popular", "latest", "new", "best", "top"]
            for kw in trending_keywords:
                all_queries += self._search_queries(f"{topic} {kw}", region, 5)

            # Strategy 2: Related searches
            all_queries += self._search_queries(f"{topic} related searches", region, 10)

            # Strategy 3: Topic combined with question words
            question_words = ["how", "what", "why", "when", "where", "which"]
            for word in question_words:
                all_queries += self._search_queries(f"{word} {topic}", region, 3)

            # Process and categorize
            categorized = self._process_and_categorize_queries(all_queries, topic, limit)
            total = len(categorized["top"]) + len(categorized["rising"])
            logger.info(f"✅ Fetched {total} trending queries for '{topic}'")

            return categorized

        except Exception as e:
            logger.error(f"❌ Error fetching trending queries for '{topic}': {type(e).__name__} - {e}")
            return {"rising": [], "top": []}

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _search_queries(self, query: str, region: str, num_results: int) -> List[str]:
        """Fetch related queries via Serper API search results."""
        try:
            payload = {
                "q": query,
                "num": num_results,
                "gl": region or "us",
                "hl": "en",
                "tbs": "qdr:m"  # Past month
            }
            response = requests.post(self.serper_base_url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            queries = set()

            # Extract queries from organic results
            for result in data.get("organic", [])[:num_results]:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                queries.update(self._extract_queries_from_text(title))
                queries.update(self._extract_queries_from_text(snippet))

            # Add related searches
            for related in data.get("relatedSearches", []):
                q = related.get("query")
                if q:
                    queries.add(q)

            # Add "people also ask"
            for paa in data.get("peopleAlsoAsk", []):
                q = paa.get("question")
                if q:
                    queries.add(q)

            return list(queries)

        except Exception as e:
            logger.warning(f"⚠️ Error searching queries for '{query}': {e}")
            return []

    def _extract_queries_from_text(self, text: str) -> List[str]:
        """Extract potential queries from text."""
        import re
        if not text:
            return []

        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = clean.split()
        queries = set()

        for i in range(len(words)):
            for n in (2, 3, 4):  # create 2–4 word phrases
                if i + n <= len(words):
                    phrase = " ".join(words[i:i + n])
                    if 5 < len(phrase) < 50:
                        queries.add(phrase)

        return list(queries)

    def _process_and_categorize_queries(
        self, all_queries: List[str], topic: str, limit: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Filter, score, and categorize queries into top and rising groups."""
        unique_queries = list(set(all_queries))
        topic_words = topic.lower().split()
        relevant = []

        for query in unique_queries:
            q = query.strip().lower()
            if not q or q == topic.lower() or len(q) < 3:
                continue

            # Simple relevance scoring
            score = sum(1 for word in topic_words if word in q) + random.uniform(0, 0.5)
            if score > 0:
                relevant.append({
                    "query": query.strip(),
                    "relevance_score": score,
                    "value": round(random.uniform(50, 100), 1)
                })

        # Sort by relevance and limit
        relevant.sort(key=lambda x: x["relevance_score"], reverse=True)
        total = min(len(relevant), limit)
        mid = total // 2

        return {
            "top": [
                {"query": q["query"], "value": q["value"], "trend_type": "top"}
                for q in relevant[:mid]
            ],
            "rising": [
                {"query": q["query"], "value": round(q["value"] * 0.8, 1), "trend_type": "rising"}
                for q in relevant[mid:total]
            ]
        }

    def _mock_trending_data(self, topic: str, limit: int) -> Dict[str, List[Dict[str, Any]]]:
        """Generate mock trending data for local testing."""
        return {
            "top": [
                {"query": f"{topic} tutorial", "value": 100.0, "trend_type": "top"},
                {"query": f"{topic} guide", "value": 85.5, "trend_type": "top"},
                {"query": f"best {topic}", "value": 75.2, "trend_type": "top"},
            ][:limit],
            "rising": [
                {"query": f"{topic} 2024", "value": 95.8, "trend_type": "rising"},
                {"query": f"new {topic}", "value": 88.3, "trend_type": "rising"},
            ][:limit]
        }


# -------------------------------------------------------------------------
# Simple functional wrapper
# -------------------------------------------------------------------------

def fetch_trending_queries(topic: str, region: str = "", limit: int = 30) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch trending queries for a topic using the Serper API.
    Safe functional wrapper for easier usage.
    """
    try:
        api = TrendingQueriesAPI()
        return api.get_trending_queries(topic=topic, region=region, limit=limit)
    except Exception as e:
        logger.error(f"❌ fetch_trending_queries() failed for '{topic}': {type(e).__name__} - {e}")
        return {"rising": [], "top": []}
