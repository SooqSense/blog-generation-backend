from .base_client import APIClient
from .blog_api import BlogAPI
from .image_api import ImageAPI
from .linkedin_api import LinkedInAPI
from .news_api import NewsAPI
from .knowledge_base_api import KnowledgeBaseAPI
from .chatbot_api import ChatbotAPI
from .upwork_api import UpworkAPI
from .schedule_api import ScheduleAPI
from .trends_api import TrendsAPI

# Initialize singletons for convenience
blog_api = BlogAPI()
image_api = ImageAPI()
linkedin_api = LinkedInAPI()
news_api = NewsAPI()
knowledge_base_api = KnowledgeBaseAPI()
chatbot_api = ChatbotAPI()
upwork_api = UpworkAPI()
schedule_api = ScheduleAPI()
trends_api = TrendsAPI()


