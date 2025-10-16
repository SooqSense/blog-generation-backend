import requests
from datetime import datetime, date
from typing import List, Dict
import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)


class AIDailyNewsService:
    """
    Service to fetch daily AI news using Serper API
    and generate structured markdown content with OpenAI.
    """

    def __init__(self):
        self.serper_api_key = settings.SERPER_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.serper_base_url = "https://google.serper.dev/news"

        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY missing from Django settings.")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY missing from Django settings.")

        self.openai_client = OpenAI(api_key=self.openai_api_key)

    # -------------------------------------------------------------------------
    # Search News
    # -------------------------------------------------------------------------

    def search_news(self, keywords: List[str], country: str = "us", num_results: int = 10) -> List[Dict]:
        """Search AI news using Serper API with multiple fallback strategies."""
        base_query = " ".join(keywords) + " AI artificial intelligence"
        headers = {"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"}

        country_terms = self._get_country_specific_terms(country)
        country_name = self._get_country_name(country)

        search_strategies = [
            {"q": f"{base_query} {country_terms}", "gl": country, "hl": "en", "num": num_results, "tbs": "qdr:d"},
            {"q": f"{base_query} {country_name}", "gl": country, "hl": "en", "num": num_results, "tbs": "qdr:d"},
            {"q": base_query, "gl": country, "hl": "en", "num": num_results, "tbs": "qdr:d"},
        ]

        for i, payload in enumerate(search_strategies, start=1):
            try:
                response = requests.post(self.serper_base_url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                news_articles = data.get("news", [])
                if news_articles:
                    if i > 1:
                        logger.info(f"Found results using fallback strategy {i} for {country}")
                    return news_articles
                else:
                    logger.info(f"No results with search strategy {i} for {country}")
            except requests.RequestException as e:
                logger.warning(f"Strategy {i} failed for {country}: {e}")
                continue

        logger.warning(f"All search strategies failed for {country}")
        return []

    # -------------------------------------------------------------------------
    # Generate Content
    # -------------------------------------------------------------------------

    def generate_news_content(self, news_articles: List[Dict], keywords: List[str], country: str) -> Dict[str, str]:
        """Generate concise daily AI news markdown using OpenAI."""
        if not news_articles:
            country_name = self._get_country_name(country)
            return {
                "summary": f"No AI news found for {country_name} today",
                "content": f"# No AI News Today\n\nNo relevant AI news articles were found for {country_name} today.",
            }

        # Prepare top 5 articles
        news_text = "\n".join(
            f"{i+1}. {a.get('title','No title')}\n   Source: {a.get('source','Unknown')}\n   Summary: {a.get('snippet','No description')}"
            for i, a in enumerate(news_articles[:5])
        )

        country_name = self._get_country_name(country)
        today_date = datetime.now().strftime("%B %d, %Y")

        system_prompt = f"""
You are an AI news summarizer focusing on {country_name}'s AI developments.
Create a short, focused markdown report with:
- A catchy tagline (1 line)
- 3–5 concise bullet points about today's {country_name}-specific AI updates
- Focus on local companies, government, or research
Limit to 300 words.
Date: {today_date}
"""

        user_prompt = f"""
Based on these AI news articles from {country_name}, write the daily summary:

{news_text}

Format:
# [Catchy tagline]
## Today's AI Highlights - {today_date}
• [Brief summary 1]
• [Brief summary 2]
• [Brief summary 3]
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()
            tagline = next(
                (line.strip("# ").strip() for line in content.splitlines() if line.strip().startswith("# ")), None
            )
            summary = tagline or f"Daily AI News - {country_name}"

            return {"summary": summary, "content": content}
        except Exception as e:
            logger.error(f"Error generating AI news summary: {e}")
            return {
                "summary": f"Error generating AI news for {country.upper()}",
                "content": f"# Error\n\nFailed to generate AI news content: {e}",
            }

    # -------------------------------------------------------------------------
    # Main Method
    # -------------------------------------------------------------------------

    def get_daily_ai_news(self, keywords: List[str], country: str = "us", num_results: int = 5) -> Dict:
        """Fetch, process, and summarize daily AI news."""
        try:
            logger.info(f"Fetching daily AI headlines for {country.upper()} | Keywords: {', '.join(keywords)}")
            news_articles = self.search_news(keywords, country, num_results)

            if not news_articles:
                return {
                    "success": False,
                    "message": "No AI news found for today",
                    "summary": "",
                    "content": "",
                    "articles_count": 0,
                    "sources": [],
                }

            sources = [
                {
                    "title": a.get("title", "No title"),
                    "source": a.get("source", "Unknown"),
                    "link": a.get("link", ""),
                    "snippet": a.get("snippet", "No description"),
                    "date": a.get("date", ""),
                    "position": a.get("position", 0),
                }
                for a in news_articles
            ]

            content_data = self.generate_news_content(news_articles, keywords, country)

            return {
                "success": True,
                "message": f"AI headlines generated for {self._get_country_name(country)}",
                "summary": content_data["summary"],
                "content": content_data["content"],
                "articles_count": len(news_articles),
                "sources": sources,
                "country": country,
                "keywords": keywords,
                "news_date": date.today().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in get_daily_ai_news: {e}")
            return {
                "success": False,
                "message": f"Error fetching daily AI news: {e}",
                "summary": "",
                "content": "",
                "articles_count": 0,
                "sources": [],
            }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_country_specific_terms(self, code: str) -> str:
        return {
            "us": "USA America Silicon Valley",
            "uk": "UK London government policy",
            "in": "India Bangalore Mumbai",
            "ca": "Canada Toronto Vancouver",
            "au": "Australia Sydney Melbourne",
            "de": "Germany Berlin Munich",
            "fr": "France Paris EU",
            "jp": "Japan Tokyo",
            "cn": "China Beijing Shanghai",
            "kr": "South Korea Seoul",
            "sg": "Singapore tech hub",
            "nl": "Netherlands Amsterdam",
            "se": "Sweden Stockholm",
            "ch": "Switzerland Zurich",
            "il": "Israel Tel Aviv",
        }.get(code.lower(), "")

    def _get_country_name(self, code: str) -> str:
        return {
            "us": "United States",
            "uk": "United Kingdom",
            "in": "India",
            "ca": "Canada",
            "au": "Australia",
            "de": "Germany",
            "fr": "France",
            "jp": "Japan",
            "cn": "China",
            "kr": "South Korea",
            "sg": "Singapore",
            "nl": "Netherlands",
            "se": "Sweden",
            "ch": "Switzerland",
            "il": "Israel",
        }.get(code.lower(), code.upper())
