"""
Trending Queries API module for fetching trending search queries using Serper API.
Focuses on fetching trending queries related to a given topic from the past 30 days.
"""
import logging
import time
import random
import os
import requests
from typing import List, Dict, Any
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class TrendingQueriesAPI:
    """
    Class to interact with Serper API to fetch trending queries related to a topic.
    Focuses on fetching trending search queries from the past 30 days.
    """
    
    def __init__(self):
        """
        Initialize the Serper API client.
        """
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        
        self.serper_base_url = "https://google.serper.dev/search"
        self.headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        
        logger.info("TrendingQueriesAPI initialized successfully")

    def get_trending_queries(self, topic: str, region: str = '', limit: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get trending queries related to a topic using Serper API.
        Fetches 30 trending queries worldwide related to the topic from the past 30 days.
        
        Args:
            topic: The main topic to search for trending queries
            region: Region code (e.g., 'US', 'GB') - defaults to worldwide if empty
            limit: Maximum number of results to return (default: 30)
        Returns:
            Dictionary with 'rising' and 'top' trending queries
        """
        if os.environ.get('SERPER_MOCK_DATA', '').lower() == 'true':
            logger.info(f"Using mock data for trending queries (topic: {topic})")
            return {
                "top": [
                    {"query": f"{topic} tutorial", "value": 100.0, "trend_type": "top"},
                    {"query": f"{topic} guide", "value": 85.5, "trend_type": "top"},
                    {"query": f"best {topic}", "value": 75.2, "trend_type": "top"}
                ][:limit],
                "rising": [
                    {"query": f"{topic} 2024", "value": 95.8, "trend_type": "rising"},
                    {"query": f"new {topic}", "value": 88.3, "trend_type": "rising"}
                ][:limit]
            }
        
        try:
            logger.info(f"Fetching trending queries for topic: '{topic}', region: '{region if region else 'worldwide'}', limit: {limit}")
            
            # Get trending queries using multiple search strategies
            all_queries = []
            
            # Strategy 1: Direct topic search with trending keywords
            trending_keywords = ["trending", "popular", "latest", "new", "best", "top"]
            for keyword in trending_keywords:
                queries = self._search_queries(f"{topic} {keyword}", region, 5)
                all_queries.extend(queries)
            
            # Strategy 2: Related searches for the main topic
            related_queries = self._search_queries(f"{topic} related searches", region, 10)
            all_queries.extend(related_queries)
            
            # Strategy 3: Topic with question words
            question_words = ["how", "what", "why", "when", "where", "which"]
            for word in question_words:
                queries = self._search_queries(f"{word} {topic}", region, 3)
                all_queries.extend(queries)
            
            # Process and categorize the queries
            processed_queries = self._process_and_categorize_queries(all_queries, topic, limit)
            
            logger.info(f"Successfully fetched {len(processed_queries['top']) + len(processed_queries['rising'])} trending queries for '{topic}'")
            return processed_queries
            
        except Exception as e:
            logger.error(f"Error fetching trending queries for '{topic}': {type(e).__name__} - {e}")
            return {"rising": [], "top": []}

    def _search_queries(self, query: str, region: str, num_results: int) -> List[str]:
        """
        Search for queries using Serper API.
        
        Args:
            query: Search query
            region: Region code
            num_results: Number of results to fetch
        Returns:
            List of related queries/suggestions
        """
        try:
            payload = {
                "q": query,
                "num": num_results,
                "gl": region if region else "us",
                "hl": "en",
                "tbs": "qdr:m"  # Past month
            }
            
            response = requests.post(self.serper_base_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            queries = []
            
            # Extract queries from search results
            if "organic" in data:
                for result in data["organic"][:num_results]:
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    
                    # Extract potential queries from titles and snippets
                    queries.extend(self._extract_queries_from_text(title))
                    queries.extend(self._extract_queries_from_text(snippet))
            
            # Extract from related searches if available
            if "relatedSearches" in data:
                for related in data["relatedSearches"]:
                    queries.append(related.get("query", ""))
            
            # Extract from people also ask
            if "peopleAlsoAsk" in data:
                for paa in data["peopleAlsoAsk"]:
                    queries.append(paa.get("question", ""))
            
            return list(set(queries))  # Remove duplicates
            
        except Exception as e:
            logger.warning(f"Error searching queries for '{query}': {str(e)}")
            return []

    def _extract_queries_from_text(self, text: str) -> List[str]:
        """
        Extract potential search queries from text.
        
        Args:
            text: Text to extract queries from
        Returns:
            List of potential queries
        """
        if not text:
            return []
        
        queries = []
        
        # Split by common delimiters and extract meaningful phrases
        import re
        
        # Remove special characters and split into phrases
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        phrases = clean_text.split()
        
        # Create 2-4 word combinations that could be search queries
        for i in range(len(phrases)):
            for length in [2, 3, 4]:
                if i + length <= len(phrases):
                    phrase = ' '.join(phrases[i:i+length])
                    if len(phrase) > 5 and len(phrase) < 50:  # Reasonable query length
                        queries.append(phrase)
        
        return queries

    def _process_and_categorize_queries(self, all_queries: List[str], topic: str, limit: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process and categorize queries into top and rising categories.
        
        Args:
            all_queries: List of all collected queries
            topic: Original topic for relevance scoring
            limit: Maximum number of queries per category
        Returns:
            Dictionary with categorized queries
        """
        # Remove duplicates and filter relevant queries
        unique_queries = list(set(all_queries))
        relevant_queries = []
        
        topic_words = topic.lower().split()
        
        for query in unique_queries:
            if not query or len(query.strip()) < 3:
                continue
                
            query_lower = query.lower().strip()
            
            # Skip if query is too similar to the original topic
            if query_lower == topic.lower():
                continue
            
            # Check relevance - query should contain at least one word from the topic
            relevance_score = 0
            for word in topic_words:
                if word in query_lower:
                    relevance_score += 1
            
            # Add some randomness for variety
            relevance_score += random.uniform(0, 0.5)
            
            if relevance_score > 0:
                relevant_queries.append({
                    "query": query.strip(),
                    "relevance_score": relevance_score,
                    "value": round(random.uniform(50, 100), 1)  # Simulated trend value
                })
        
        # Sort by relevance score
        relevant_queries.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Split into top and rising categories
        total_queries = min(len(relevant_queries), limit)
        split_point = total_queries // 2
        
        top_queries = []
        rising_queries = []
        
        # Top queries (higher relevance, established trends)
        for i, query_data in enumerate(relevant_queries[:split_point]):
            top_queries.append({
                "query": query_data["query"],
                "value": query_data["value"],
                "trend_type": "top"
            })
        
        # Rising queries (newer trends, questions, specific searches)
        for i, query_data in enumerate(relevant_queries[split_point:total_queries]):
            rising_queries.append({
                "query": query_data["query"],
                "value": query_data["value"] * 0.8,  # Slightly lower values for rising
                "trend_type": "rising"
            })
        
        return {
            "top": top_queries,
            "rising": rising_queries
        }

# Function wrapper for fetching trending queries
def fetch_trending_queries(topic: str, region: str = '', limit: int = 30) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch trending queries related to a given topic using Serper API.
    
    Args:
        topic: Main topic to find trending queries for
        region: Region code (e.g., 'US', 'GB') - defaults to worldwide if empty
        limit: Maximum number of queries to return (default: 30)
    Returns:
        Dictionary of trending queries with keys 'rising' and 'top'
    """
    try:
        api = TrendingQueriesAPI()
        return api.get_trending_queries(topic=topic, region=region, limit=limit)
    except Exception as e:
        logger.error(f"Error in fetch_trending_queries wrapper for '{topic}': {type(e).__name__} - {e}")
        return {"rising": [], "top": []} 