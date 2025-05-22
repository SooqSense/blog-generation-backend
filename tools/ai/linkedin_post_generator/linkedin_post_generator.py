import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, crew, task
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# Define the base directory for this service module
SERVICE_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_OUTPUT_DIR = os.path.join(SERVICE_BASE_DIR, 'posts')

@CrewBase
class LinkedInPostGenerator:
    """A crew for generating LinkedIn posts."""

    def __init__(self, use_custom_llm=False, topic=None, keywords=None):
        self.use_custom_llm = use_custom_llm
        self.topic = topic
        self.keywords = keywords if keywords else []

        if use_custom_llm:
            gemini_api_key = os.getenv("GOOGLE_API_KEY")
            if not gemini_api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment variables for custom LLM.")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=gemini_api_key,
                temperature=0.7,
            )
        else:
            # Default to OpenAI GPT 3.5 Turbo
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY not found in environment variables for default LLM.")
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7
            )

    @agent
    def linkedin_post_writer_agent(self):
        return Agent(
            role="LinkedIn Content Strategist",
            goal="""Craft a professional, elegant, and impactful LinkedIn post for the given topic.
            The post must be structured as exactly two distinct paragraphs followed by hashtags.
            Each paragraph should offer insight or value. No headers, titles, or metadata should be included.
            The post must include strategic emojis and end with relevant hashtags only.""",
            backstory="""You are an elite LinkedIn content creator, renowned for writing concise, high-impact posts
            that drive engagement. You create clean, direct professional content with no unnecessary formatting.
            Your posts always follow the exact same structure: two paragraphs with emojis integrated naturally
            within the text, followed by relevant hashtags. You never include explanations, headers, or metadata.""",
            verbose=True,
            llm=self.llm,
            allow_delegation=False
        )

    @task
    def linkedin_generation_task(self):
        topic_placeholder = self.topic if self.topic else "{topic}"
        keywords_text = ""
        if self.keywords and len(self.keywords) > 0:
            keywords_text = f" You MUST incorporate these specific keywords: {', '.join(self.keywords)}."
        
        return Task(
            description=f"""Generate a LinkedIn post STRICTLY focused on the EXACT topic: "{topic_placeholder}".{keywords_text}
            
            STRICT CONTENT REQUIREMENTS:
            - Your post MUST be SPECIFICALLY about "{topic_placeholder}" - not general AI or related fields
            - STAY FOCUSED on the exact topic without drifting to broader subjects
            - If keywords are provided, you MUST incorporate ALL of them naturally in the content
            - Your content should demonstrate expertise specifically in "{topic_placeholder}"
            
            STRICT OUTPUT FORMAT:
            Paragraph 1 (with 1-2 emojis naturally integrated)
            
            Paragraph 2 (with 1-2 emojis naturally integrated)
            
            #hashtag1 #hashtag2 #hashtag3 #hashtag4
            
            REQUIREMENTS:
            1. Paragraph 1: Write 2-4 concise, professional sentences with 1-2 relevant emojis integrated naturally.
            2. Paragraph 2: Write 2-4 concise, professional sentences with 1-2 relevant emojis integrated naturally.
            3. Include exactly ONE blank line between paragraphs.
            4. End with 3-5 relevant hashtags, all lowercase, no spaces within hashtags.
            5. Use professional emojis only (e.g.: ✨, 🚀, 💡, 📈, 🤝, ✅).
            
            CRITICAL RULES:
            - START IMMEDIATELY with the first paragraph text. NO intro text like "LinkedIn post:" or "Here's a post about:"
            - NO headers or section titles in brackets like [Introduction] or [Paragraph 1]
            - NO explanations about what you've written
            - NO quotes or attribution
            - NO numbering of paragraphs
            - NEVER respond with anything except the exact format above
            - DO NOT explain your thought process
            - NEVER use bullet points
            - CREATE NEW ORIGINAL CONTENT specific to the topic "{topic_placeholder}" - DO NOT reuse this example
            - NEVER use the cybersecurity example below - it is ONLY a format reference
            
            Your entire response must be ONLY the LinkedIn post content itself, and it must be ORIGINAL for the topic "{topic_placeholder}".""",
            expected_output="""[Example format only - DO NOT COPY this content - Create original content for "{topic_placeholder}"]

Are you leveraging digital marketing to its full potential? In today's competitive landscape, a comprehensive strategy that combines content marketing, SEO, and social media engagement is essential for building brand awareness. Investing time in understanding your audience's online behavior can transform your approach from generic to laser-focused, resulting in higher conversion rates and authentic brand connections. ✨

Remember that consistency is key in digital marketing. Creating a content calendar, establishing a clear brand voice, and regularly analyzing performance metrics will help you adapt and evolve your strategy effectively. The digital landscape changes rapidly, but businesses that remain adaptable while staying true to their core values will navigate these shifts successfully and build lasting customer relationships. 🚀

#digitalmarketing #contentcreation #brandstrategy #onlineengagement""".format(topic_placeholder=topic_placeholder),
            agent=self.linkedin_post_writer_agent()
        )

    def generate_post(self, topic: str, keywords=None):
        """Generates a LinkedIn post for a given topic and returns the content."""
        if not topic:
            raise ValueError("Topic must be provided for LinkedIn post generation.")

        # Update the instance topic
        self.topic = topic
        self.keywords = keywords if keywords else []

        # Create a fresh agent and task for each generation to avoid any caching issues
        writer_agent = self.linkedin_post_writer_agent()
        generation_task = self.linkedin_generation_task()
        
        # Configure the crew with these fresh instances
        linkedin_crew = Crew(
            agents=[writer_agent],
            tasks=[generation_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Explicitly set the temperature higher to encourage more variation
        if hasattr(self.llm, 'temperature'):
            original_temp = self.llm.temperature
            self.llm.temperature = 0.8
            
        # Force topic into inputs and add randomness parameter to avoid cached responses
        import random
        post_content_raw = str(linkedin_crew.kickoff(
            inputs={
                "topic": topic,
                "variation_key": str(random.randint(1000, 9999))  # Add randomness to prevent caching
            }
        )).strip()
        
        # Restore original temperature if we changed it
        if hasattr(self.llm, 'temperature') and 'original_temp' in locals():
            self.llm.temperature = original_temp

        # Enhanced cleanup for more aggressive formatting removal
        if post_content_raw:
            # Remove any potential prefix text (common patterns)
            prefixes = [
                "LinkedIn post:", "Here's a LinkedIn post:", "LinkedIn Post:", 
                "Post:", "Here is a LinkedIn post:", "Here's the LinkedIn post:",
                "Content:", "LinkedIn content:", "Here's the content:"
            ]
            for prefix in prefixes:
                if post_content_raw.startswith(prefix):
                    post_content_raw = post_content_raw[len(prefix):].strip()
            
            # Remove any titles, headers, or section labels in various formats
            post_content_raw = re.sub(r'^\s*\[.*?\]\s*', '', post_content_raw, flags=re.MULTILINE)
            post_content_raw = re.sub(r'^\s*Title:.*$', '', post_content_raw, flags=re.MULTILINE)
            post_content_raw = re.sub(r'^\s*Paragraph \d+:?\s*', '', post_content_raw, flags=re.MULTILINE)
            post_content_raw = re.sub(r'^\s*Introduction:?\s*', '', post_content_raw, flags=re.MULTILINE)
            post_content_raw = re.sub(r'^\s*Conclusion:?\s*', '', post_content_raw, flags=re.MULTILINE)
            post_content_raw = re.sub(r'^\s*Hashtags:?\s*', '', post_content_raw, flags=re.MULTILINE)
            
            # Remove any bullet points or numbered lists
            post_content_raw = re.sub(r'^\s*[-•*]\s+', '', post_content_raw, flags=re.MULTILINE)
            post_content_raw = re.sub(r'^\s*\d+[.)\]]\s+', '', post_content_raw, flags=re.MULTILINE)
            
            # Remove any trailing explanations or notes
            explanation_patterns = [
                r'\n\s*Note:.*$',
                r'\n\s*This post.*$', 
                r'\n\s*The above.*$',
                r'\n\s*I hope.*$',
                r'\n\s*Feel free.*$'
            ]
            for pattern in explanation_patterns:
                post_content_raw = re.sub(pattern, '', post_content_raw, flags=re.DOTALL)
            
            # Process hashtags to ensure they're lowercase and properly formatted
            lines = post_content_raw.split('\n')
            processed_lines = []
            
            for line in lines:
                if any(word.startswith('#') for word in line.split()):
                    # This is a hashtag line
                    words = []
                    for word in line.split():
                        if word.startswith('#'):
                            # Convert hashtag to lowercase
                            words.append(word.lower())
                        else:
                            words.append(word)
                    processed_lines.append(' '.join(words))
                else:
                    processed_lines.append(line)
            
            # Remove consecutive blank lines
            cleaned_lines = []
            prev_blank = False
            for line in processed_lines:
                is_blank = not line.strip()
                if not (is_blank and prev_blank):
                    cleaned_lines.append(line)
                prev_blank = is_blank
                
            post_content = '\n'.join(cleaned_lines).strip()
        else:
            post_content = ""

        # Return the generated post content and None for file path since we're not saving to a file
        return post_content, None

# Example Usage (for direct testing of this file)
if __name__ == '__main__':
    try:
        generator = LinkedInPostGenerator(use_custom_llm=False)
        sample_topic = "The Future of Renewable Energy"
        post, file_path = generator.generate_post(sample_topic)
        print("\n--- Generated LinkedIn Post ---")
        print(post)
        if file_path:
            print(f"\nSaved to: {file_path}")
        print("\n-----------------------------")
    except Exception as e:
        print(f"Error: {e}")
