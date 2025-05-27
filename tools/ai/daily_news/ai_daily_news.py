import os
import requests
from datetime import datetime, date
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

class AIDailyNewsService:
    """
    Service to fetch daily AI news from various countries and keywords using Serper API
    and generate structured markdown content.
    """
    
    def __init__(self):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.serper_api_key:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.serper_base_url = "https://google.serper.dev/news"
    
    def search_news(self, keywords: List[str], country: str = "us", num_results: int = 10) -> List[Dict]:
        """
        Search for news articles using Serper API with enhanced country-specific filtering
        
        Args:
            keywords: List of keywords to search for
            country: Country code (e.g., 'us', 'uk', 'in', 'ca')
            num_results: Number of results to fetch
            
        Returns:
            List of news articles
        """
        try:
            # Get country-specific search terms
            country_terms = self._get_country_specific_terms(country)
            country_name = self._get_country_name(country)
            
            # Combine keywords with country-specific terms
            base_query = " ".join(keywords) + " AI artificial intelligence"
            
            headers = {
                "X-API-KEY": self.serper_api_key,
                "Content-Type": "application/json"
            }
            
            # Try multiple search strategies
            search_strategies = [
                # Strategy 1: Country-specific with location terms
                {
                    "q": f"{base_query} {country_terms}" if country_terms else base_query,
                    "gl": country,
                    "hl": "en",
                    "num": num_results,
                    "tbs": "qdr:d"
                },
                # Strategy 2: Country name in query without strict geo-location
                {
                    "q": f"{base_query} {country_name}",
                    "gl": country,
                    "hl": "en", 
                    "num": num_results,
                    "tbs": "qdr:d"
                },
                # Strategy 3: Broader search with country preference
                {
                    "q": base_query,
                    "gl": country,
                    "hl": "en",
                    "num": num_results,
                    "tbs": "qdr:d"
                }
            ]
            
            for i, payload in enumerate(search_strategies, 1):
                try:
                    response = requests.post(self.serper_base_url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    data = response.json()
                    news_articles = data.get("news", [])
                    
                    if news_articles:
                        if i > 1:
                            print(f"Found results using search strategy {i} for {country}")
                        return news_articles
                    else:
                        print(f"Search strategy {i} returned no results for {country}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"Search strategy {i} failed for {country}: {str(e)}")
                    continue
            
            print(f"All search strategies failed for {country}")
            return []
            
        except Exception as e:
            print(f"Error fetching news: {str(e)}")
            return []
    
    def generate_news_content(self, news_articles: List[Dict], keywords: List[str], country: str) -> Dict[str, str]:
        """
        Generate simplified daily AI news with tagline and concise summary
        
        Args:
            news_articles: List of news articles from Serper API
            keywords: Keywords used for search
            country: Country code
            
        Returns:
            Dictionary with 'summary' and 'content' keys
        """
        try:
            if not news_articles:
                return {
                    "summary": f"No AI news found for {country.upper()} today",
                    "content": f"# No AI News Today\n\nNo relevant AI news articles were found for {self._get_country_name(country)} today."
                }
            
            # Prepare concise news data for AI processing
            news_text = ""
            for i, article in enumerate(news_articles[:5], 1):  # Limit to top 5 articles for brevity
                title = article.get("title", "No title")
                snippet = article.get("snippet", "No description")
                source = article.get("source", "Unknown source")
                
                news_text += f"""
{i}. {title}
   Source: {source}
   Summary: {snippet}
"""
            
            # Create AI prompt for simplified content generation
            country_name = self._get_country_name(country)
            today_date = datetime.now().strftime('%B %d, %Y')
            
            system_prompt = f"""You are an AI news summarizer specializing in country-specific AI developments. Create a concise daily AI news summary with:

1. A catchy tagline (one sentence) that reflects {country_name}-specific AI developments
2. Brief bullet points focusing on AI news most relevant to {country_name}
3. Prioritize local companies, government policies, and regional developments
4. Keep it short and focused on the most important news for {country_name}

Focus on:
- Local AI companies and startups in {country_name}
- Government AI policies and regulations in {country_name}
- AI research from {country_name} universities/institutions
- Regional AI market developments
- Local tech industry news

Use simple markdown formatting.
Keep the entire content under 300 words.
If no country-specific news is available, mention the most relevant global AI news with {country_name} context.

Country Focus: {country_name}
Date: {today_date}"""

            user_prompt = f"""Based on these AI news articles from {country_name}, create a brief daily summary:

{news_text}

Format:
# [Catchy Tagline about today's AI news]

## Today's AI Headlines - {today_date}

• [Brief point about most important news]
• [Brief point about second most important news]
• [Brief point about third most important news if relevant]

Keep it concise and focus only on the most significant developments."""

            # Generate content using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500  # Reduced token limit for shorter content
            )
            
            generated_content = response.choices[0].message.content.strip()
            
            # Extract tagline (first line after #)
            lines = generated_content.split('\n')
            tagline = ""
            
            for line in lines:
                if line.strip().startswith('#') and not line.strip().startswith('##'):
                    tagline = line.strip().replace('#', '').strip()
                    break
            
            summary = tagline if tagline else f"Daily AI news for {country_name} - {today_date}"
            
            return {
                "summary": summary,
                "content": generated_content
            }
            
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            return {
                "summary": f"Error generating AI news for {country.upper()}",
                "content": f"# Error\n\nFailed to generate AI news content: {str(e)}"
            }
    
    def _get_country_specific_terms(self, country_code: str) -> str:
        """Get country-specific search terms to improve localization"""
        country_terms = {
            "us": "USA America Silicon Valley tech companies startups",
            "uk": "Britain UK London tech sector government policy",
            "in": "India Bangalore Mumbai tech industry government",
            "ca": "Canada Toronto Vancouver tech sector policy",
            "au": "Australia Sydney Melbourne tech industry",
            "de": "Germany Berlin Munich tech industry EU policy",
            "fr": "France Paris tech industry EU regulation",
            "jp": "Japan Tokyo tech industry government",
            "cn": "China Chinese tech Baidu Alibaba Tencent ByteDance",  # Focus on major Chinese tech companies
            "kr": "South Korea Seoul tech industry Samsung LG",
            "sg": "Singapore tech hub Southeast Asia",
            "nl": "Netherlands Amsterdam tech industry EU",
            "se": "Sweden Stockholm tech industry Nordic",
            "ch": "Switzerland Zurich tech industry",
            "il": "Israel Tel Aviv tech industry startup"
        }
        return country_terms.get(country_code.lower(), "")

    def _get_country_name(self, country_code: str) -> str:
        """Convert country code to country name"""
        country_map = {
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
            "il": "Israel"
        }
        return country_map.get(country_code.lower(), country_code.upper())
    
    def get_daily_ai_news(self, keywords: List[str], country: str = "us", num_results: int = 5) -> Dict:
        """
        Main method to fetch and process daily AI news headlines
        
        Args:
            keywords: List of keywords to search for
            country: Country code for news filtering
            num_results: Number of news articles to fetch (default: 5 for concise daily summary)
            
        Returns:
            Dictionary with processed news data
        """
        try:
            print(f"Fetching daily AI headlines for {country.upper()} with keywords: {', '.join(keywords)}")
            
            # Fetch news articles
            news_articles = self.search_news(keywords, country, num_results)
            
            if not news_articles:
                print("No news articles found")
                return {
                    "success": False,
                    "message": "No AI news found for today",
                    "summary": "",
                    "content": "",
                    "articles_count": 0
                }
            
            print(f"Found {len(news_articles)} news articles")
            
            # Generate content
            content_data = self.generate_news_content(news_articles, keywords, country)
            
            return {
                "success": True,
                "message": f"Successfully generated daily AI headlines for {self._get_country_name(country)}",
                "summary": content_data["summary"],
                "content": content_data["content"],
                "articles_count": len(news_articles),
                "country": country,
                "keywords": keywords,
                "news_date": date.today().isoformat()
            }
            
        except Exception as e:
            print(f"Error in get_daily_ai_news: {str(e)}")
            return {
                "success": False,
                "message": f"Error fetching daily AI news: {str(e)}",
                "summary": "",
                "content": "",
                "articles_count": 0
            }

# Example usage
if __name__ == "__main__":
    service = AIDailyNewsService()
    
    # Test with sample data
    keywords = ["artificial intelligence", "machine learning", "AI startups"]
    country = "us"
    
    result = service.get_daily_ai_news(keywords, country)
    
    if result["success"]:
        print("Summary:", result["summary"])
        print("\nContent:")
        print(result["content"])
    else:
        print("Error:", result["message"])
