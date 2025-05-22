"""
PyTrends API module for fetching Google Trends data.
Focuses on fetching related topics for a given keyword.
"""
import logging
import time
import random
import os
import pandas as pd
from pytrends.request import TrendReq
from typing import List, Dict, Any
import json # Added for JSON operations
from datetime import datetime # Added for timestamping

# Set up logging
logger = logging.getLogger(__name__)

# Define a base directory for storing raw Pytrends responses
# In a Django project, you might get this from settings:
# from django.conf import settings
# PYTRENDS_RAW_RESPONSES_DIR = getattr(settings, 'PYTRENDS_RAW_RESPONSES_DIR', os.path.join(settings.BASE_DIR, 'pytrends_raw_responses'))
# For this standalone example, let's assume a path.
# IMPORTANT: Ensure this path exists or is created.
# For a general solution, we can use the current working directory or a known path.
# Let's use a subfolder in the current script's directory for simplicity here.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTRENDS_RAW_RESPONSES_DIR = os.path.join(SCRIPT_DIR, 'pytrends_raw_responses')
if not os.path.exists(PYTRENDS_RAW_RESPONSES_DIR):
    try:
        os.makedirs(PYTRENDS_RAW_RESPONSES_DIR)
        logger.info(f"Created directory for Pytrends raw responses: {PYTRENDS_RAW_RESPONSES_DIR}")
    except OSError as e:
        logger.error(f"Failed to create directory {PYTRENDS_RAW_RESPONSES_DIR}: {e}")
        PYTRENDS_RAW_RESPONSES_DIR = None # Fallback if creation fails

# Simple function to create a PyTrends instance
def get_pytrends_instance(hl='en-US', tz=360):
    """
    Creates a PyTrends instance.
    Args:
        hl: Language
        tz: Timezone offset
    Returns:
        TrendReq instance
    """
    try:
        return TrendReq(hl=hl, tz=tz)
    except Exception as e:
        logger.error(f"Failed to initialize PyTrends: {str(e)}")
        raise RuntimeError(f"Could not initialize PyTrends client: {str(e)}")

class PyTrendsAPI:
    """
    Class to interact with Google Trends API using PyTrends.
    Simplified to focus on fetching related topics.
    """
    def __init__(self, hl='en-US', tz=360):
        """
        Initialize the PyTrends client.
        Args:
            hl: Language (default 'en-US')
            tz: Timezone offset (default 360)
        """
        try:
            logger.info("Initializing PyTrends client")
            self.pytrends = get_pytrends_instance(hl, tz)
            logger.info("PyTrends client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PyTrends: {type(e).__name__} - {str(e)}")
            raise RuntimeError(f"Could not initialize PyTrends client: {str(e)}") from e
        
    def build_payload(self, keyword: str, timeframe: str = 'today 3-m', geo: str = '', gprop: str = '', max_retries: int = 3):
        """
        Build the payload for PyTrends requests with retry logic.
        Args:
            keyword: Main keyword to build trends around
            timeframe: Time frame to fetch data for (default: 'today 3-m')
            geo: Region code (e.g., 'US', 'GB') - defaults to worldwide if empty
            gprop: Google property to filter on (default: web searches)
            max_retries: Maximum number of retries for rate limiting (default: 3)
        Returns:
            True if successful, False otherwise
        """
        retries = 0
        while retries < max_retries:
            try:
                logger.info(f"Building payload for keyword: '{keyword}', geo: '{geo if geo else 'worldwide'}' (attempt {retries+1}/{max_retries})")
                self.pytrends.build_payload(kw_list=[keyword], cat=0, timeframe=timeframe, geo=geo, gprop=gprop)
                logger.info(f"Successfully built payload for keyword: '{keyword}'")
                return True
            except Exception as e:
                retries += 1
                if 'too many requests' in str(e).lower() or '429' in str(e):
                    wait_time = (2 ** retries) + random.uniform(0, 1)
                    logger.warning(f"Rate limit hit, retrying in {wait_time:.2f} seconds... ({retries}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Error building PyTrends payload: {type(e).__name__} - {e}")
                    break # For non-rate-limiting errors, break early
        
        logger.error(f"Failed to build payload for keyword: '{keyword}' after {max_retries} attempts")
        return False

    def get_related_topics(self, keyword: str, region: str = '', limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get topics related to a keyword from Google Trends.
        Also saves the raw response from pytrends.related_topics() to local storage.
        Uses fallback mechanisms for keywords that might cause the Pytrends IndexError.
        Args:
            keyword: The main keyword to search for
            region: Region code (e.g., 'US', 'GB') - defaults to worldwide if empty
            limit: Maximum number of results to return (applied after fetching for each category)
        Returns:
            Dictionary of related topics with keys 'rising' and 'top'
        """
        if os.environ.get('PYTRENDS_MOCK_DATA', '').lower() == 'true':
            logger.info(f"Using mock data for related topics (keyword: {keyword})")
            # Mock data doesn't involve a raw Pytrends API call to save
            return {
                "top": [
                    {"title": "Machine Learning", "type": "Field of study", "value": 100.0, "trend_type": "top"},
                    {"title": "Deep Learning", "type": "Field of study", "value": 85.5, "trend_type": "top"}
                ][:limit],
                "rising": [
                    {"title": "ChatGPT", "type": "Application", "value": 75.2, "trend_type": "rising"}
                ][:limit]
            }
        
        # Define a list of possible keyword variations to try if the main one fails
        # Start with the original keyword
        keyword_attempts = [keyword]
        
        # If the keyword is shorter than 5 chars, it might be too vague
        # Let's add some potential expanded versions (common patterns)
        if len(keyword.split()) == 1 and len(keyword) < 10:
            if keyword.lower() == "ai":
                keyword_attempts.append("Artificial Intelligence")
            elif keyword.lower() == "ml":
                keyword_attempts.append("Machine Learning")
            elif keyword.lower() in ["crypto", "cryptocurrency"]:
                keyword_attempts.append("Bitcoin")
            
            # For single words, try to add "technology", "topic", etc.
            for suffix in [" technology", " topic", " trends"]:
                if keyword.lower() + suffix.lower() != keyword.lower():
                    keyword_attempts.append(keyword + suffix)
        
        processed_topics: Dict[str, List[Dict[str, Any]]] = {"rising": [], "top": []}
        success = False
        
        # Try each keyword variation in sequence until one works
        for attempt_keyword in keyword_attempts:
            try:
                logger.info(f"Attempting to fetch related topics for keyword: '{attempt_keyword}'")
                
                if not self.build_payload(attempt_keyword, geo=region):
                    logger.warning(f"Payload build failed for keyword: '{attempt_keyword}', trying next fallback if available")
                    continue  # Try the next keyword variation
                
                # Fetch the raw related topics data
                related_topics_result = self.pytrends.related_topics()
                
                # --- Save the raw response ---
                if PYTRENDS_RAW_RESPONSES_DIR:
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        # Sanitize keyword for filename (replace spaces, special chars)
                        safe_keyword = "".join(c if c.isalnum() else "_" for c in attempt_keyword)
                        filename = f"{safe_keyword}_{timestamp}_related_topics.json"
                        filepath = os.path.join(PYTRENDS_RAW_RESPONSES_DIR, filename)

                        # Convert DataFrames to a serializable format (list of dicts)
                        serializable_result = {}
                        if isinstance(related_topics_result, dict):
                            for k, v_dict in related_topics_result.items(): # k is usually the keyword
                                serializable_result[k] = {}
                                if isinstance(v_dict, dict):
                                    for sub_key, df_or_val in v_dict.items(): # sub_key is 'top' or 'rising'
                                        if isinstance(df_or_val, pd.DataFrame):
                                            serializable_result[k][sub_key] = df_or_val.to_dict(orient='records')
                                        else:
                                            serializable_result[k][sub_key] = df_or_val # if it's not a DataFrame, keep as is
                                else:
                                    serializable_result[k] = v_dict

                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(serializable_result if serializable_result else related_topics_result, f, ensure_ascii=False, indent=4)
                        logger.info(f"Successfully saved raw Pytrends related_topics response for '{attempt_keyword}' to {filepath}")
                    except Exception as save_e:
                        logger.error(f"Failed to save raw Pytrends response for '{attempt_keyword}': {type(save_e).__name__} - {save_e}", exc_info=True)
                # --- End of saving raw response ---
                
                # Reset processed_topics for each attempt
                processed_topics = {"rising": [], "top": []}
                
                # IMPORTANT: Check for the keyword actually used in the payload, not our original
                # Because Pytrends might alter casing/format, get the first/only key 
                result_keyword = list(related_topics_result.keys())[0] if related_topics_result and isinstance(related_topics_result, dict) and len(related_topics_result) > 0 else attempt_keyword
                
                # Now process the results
                if result_keyword in related_topics_result and isinstance(related_topics_result[result_keyword], dict):
                    for category in ['top', 'rising']:
                        category_topics: List[Dict[str, Any]] = []
                        if category in related_topics_result[result_keyword]:
                            df_candidate = related_topics_result[result_keyword][category]
                            if isinstance(df_candidate, pd.DataFrame) and not df_candidate.empty:
                                if 'topic_title' in df_candidate.columns and 'value' in df_candidate.columns:
                                    for _, row in df_candidate.iterrows():
                                        category_topics.append({
                                            'title': row.get('topic_title', ''),
                                            'type': row.get('topic_type', ''),
                                            'value': float(row.get('value', 0)),
                                        })
                                else:
                                    logger.warning(f"DataFrame for keyword '{result_keyword}', category '{category}' is missing expected columns ('topic_title', 'value'). Columns found: {df_candidate.columns.tolist()}")
                            elif df_candidate is not None and not isinstance(df_candidate, pd.DataFrame):
                                logger.warning(f"Expected a DataFrame for keyword '{result_keyword}', category '{category}', but got {type(df_candidate)}.")
                            
                            # Only set this category's topics if we found any
                            if category_topics:
                                processed_topics[category] = sorted(category_topics, key=lambda x: x['value'], reverse=True)[:limit]
                    
                    # If we have found any topics, consider this a success
                    if processed_topics['top'] or processed_topics['rising']:
                        logger.info(f"Successfully found topics for '{result_keyword}' (original query: '{keyword}')")
                        success = True
                        # Add a note if we used a different keyword than requested
                        if attempt_keyword != keyword:
                            processed_topics['note'] = f"Used '{attempt_keyword}' as a fallback for original keyword '{keyword}'"
                        break  # Exit the loop as we found topics
                    else:
                        logger.warning(f"No topics found in response for '{result_keyword}' despite successful API call")
                else:
                    logger.warning(f"No related topics data structure found for keyword: '{result_keyword}', or it's not a dictionary")
                
            except IndexError as ie:
                # This specifically catches IndexErrors, common from Pytrends with no/sparse data
                logger.warning(
                    f"Pytrends internal IndexError for keyword '{attempt_keyword}' (likely no data or malformed response from Google): {type(ie).__name__} - {str(ie)}. Trying next fallback if available.",
                    exc_info=True
                )
                # Continue to the next keyword attempt - don't exit the loop
                continue
            
            except Exception as e:
                # Catch other, potentially more unexpected errors
                logger.error(
                    f"Unexpected error fetching related topics for '{attempt_keyword}': {type(e).__name__} - {e}",
                    exc_info=True
                )
                # For unexpected errors, try the next keyword attempt
                continue
        
        # After trying all variations, if none worked:
        if not success and (not processed_topics['top'] and not processed_topics['rising']):
            logger.warning(f"No successful results found for original keyword '{keyword}' or any of its variations: {keyword_attempts[1:] if len(keyword_attempts) > 1 else 'No variations tried'}")
        
        return processed_topics

# Function wrapper for fetching related topics
def fetch_related_topics(topic: str, region: str = '', limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch topics related to a given topic using Google Trends.
    Args:
        topic: Main topic to find related topics for
        region: Region code (e.g., 'US', 'GB') - defaults to worldwide if empty
        limit: Maximum number of topics to return per category
    Returns:
        Dictionary of related topics with keys 'rising' and 'top'
    """
    try:
        api = PyTrendsAPI()
        return api.get_related_topics(keyword=topic, region=region, limit=limit)
    except Exception as e:
        logger.error(f"Error in fetch_related_topics wrapper for '{topic}': {type(e).__name__} - {e}")
        return {"rising": [], "top": []}
