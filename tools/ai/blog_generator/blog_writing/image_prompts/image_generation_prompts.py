from crewai import Task
from ..prompts.prompts import BlogWriterPrompts


class ImageGenerationPrompts:
    """Handles image generation tasks for blog content using centralized prompts"""
    
    def __init__(self, topic, blog_type, max_image_prompts):
        self.topic = topic
        self.blog_type = blog_type
        self.max_image_prompts = max_image_prompts
    
    def create_image_prompt_generation_task(self, agent, writing_task, editing_task):
        """Create the image prompt generation task using centralized prompts"""
        return Task(
            description=BlogWriterPrompts.get_image_prompt_generation_prompt(
                self.topic, self.blog_type, self.max_image_prompts
            ),
            expected_output=BlogWriterPrompts.get_image_prompt_expected_output(
                self.topic, self.blog_type, self.max_image_prompts
            ),
            agent=agent,
            context=[writing_task, editing_task]  # Depend on the written content
        )
