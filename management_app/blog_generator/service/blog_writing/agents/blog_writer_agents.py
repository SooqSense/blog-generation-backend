from crewai import Agent
from crewai_tools import SerperDevTool


class BlogWriterAgents:
    """Agents for the blog writing crew"""
    
    def __init__(self, llm, search_tool, topic, blog_type, length_min, length_max, max_image_prompts):
        self.llm = llm
        self.search_tool = search_tool
        self.topic = topic
        self.blog_type = blog_type
        self.length_min = length_min
        self.length_max = length_max
        self.max_image_prompts = max_image_prompts
    
    def researcher(self):
        return Agent(
            role="Content Researcher",
            goal=f"Research and gather comprehensive information about {self.topic} using Google search to find top-ranked blogs and reliable sources",
            backstory="You are an expert researcher who uses SERPER API to find the most relevant and authoritative sources on any topic. You analyze search results to extract key insights and reliable information for content creation.",
            verbose=True,
            llm=self.llm,
            tools=[self.search_tool]
        )
            
    def planner(self):
        return Agent(
            role="Content Planner",
            goal=f"Create a comprehensive outline for a {self.length_min}-{self.length_max} word {self.blog_type.lower()} blog post about {self.topic} based on researched information",
            backstory="You are an experienced content strategist who creates detailed outlines based on research findings. You specialize in creating structured plans that result in engaging, well-researched blog posts.",
            verbose=True,
            llm=self.llm,
            tools=[]
        )
    
    def writer(self):
        return Agent(
            role="Content Writer",
            goal=f"Write a comprehensive {self.length_min}-{self.length_max} word {self.blog_type.lower()} blog post about {self.topic} based on research and outline",
            backstory="You are a skilled content writer who creates engaging, informative blog posts using researched information. You excel at different blog types and always include proper source citations.",
            verbose=True,
            llm=self.llm
        )
    
    def editor(self):
        return Agent(
            role="Content Editor",
            goal=f"Review and enhance the {self.blog_type.lower()} blog post to ensure it meets quality standards, includes proper sources, and follows {self.blog_type.lower()} blog format requirements",
            backstory="You are an experienced editor who improves content quality, ensures proper structure, verifies source citations, and confirms the blog follows the specified type format.",
            verbose=True,
            llm=self.llm
        )
    
    def image_prompt_generator(self):
        return Agent(
            role="Content-Aware Visual Strategist",
            goal=f"Analyze the written {self.blog_type.lower()} blog content and generate {self.max_image_prompts} highly specific, content-based AI image generation prompts",
            backstory="You are an expert visual content strategist who specializes in reading and analyzing written content to create precise AI image generation prompts. You excel at identifying key visual elements within blog posts and translating specific content details into actionable prompts for DALL-E, Midjourney, and Stable Diffusion. You understand how to match visual styles to content types and create images that directly support and enhance the written material. Your strength is in analyzing actual content rather than creating generic visuals.",
            verbose=True,
            llm=self.llm
        )
