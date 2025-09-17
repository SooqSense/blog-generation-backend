from crewai import Task
from ..prompts.prompts import BlogWriterPrompts


class BlogWriterTasks:
    """Tasks for the blog writing crew"""
    
    def __init__(self, topic, blog_type, length_min, length_max, introduction, table_of_content, 
                 faq, cta, conclusion, target_audience, keywords,
                 process_keywords_func, analyze_sample_blog_func):
        self.topic = topic
        self.blog_type = blog_type
        self.length_min = length_min
        self.length_max = length_max
        self.introduction = introduction
        self.table_of_content = table_of_content
        self.faq = faq
        self.cta = cta
        self.conclusion = conclusion
        self.target_audience = target_audience
        self.keywords = keywords
        self.process_keywords_with_counts = process_keywords_func
        self.analyze_sample_blog = analyze_sample_blog_func

    def research_task(self, agents):
        description = BlogWriterPrompts.get_research_prompt(self.topic, self.blog_type)
        expected_output = BlogWriterPrompts.get_research_expected_output(self.topic, self.blog_type)

        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.researcher()
        )
    
    def planning_task(self, agents):
        description = BlogWriterPrompts.get_planning_prompt(
            self.topic, self.blog_type, self.length_min, self.length_max,
            self.introduction, self.table_of_content, self.faq, self.cta, self.conclusion
        )
                
        # Add specifications based on parameters
        blog_specifications = []
        
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"Target audience: {audience_str}")
            
        if self.keywords:
            keywords_list, keywords_instruction = self.process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(keywords_instruction)
        
        # Add sample blog analysis if available
        sample_blog_instructions = self.analyze_sample_blog()
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        if blog_specifications:
            description += "\n\nADDITIONAL REQUIREMENTS:\n" + "\n".join(blog_specifications)
                
        expected_output = BlogWriterPrompts.get_planning_expected_output(
            self.topic, self.blog_type, self.length_min, self.length_max
        )
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.planner()
        )
    
    def writing_task(self, agents):
        
        description = BlogWriterPrompts.get_writing_prompt(
            self.topic, self.blog_type, self.length_min, self.length_max,
            self.introduction, self.table_of_content, self.faq, self.cta, self.conclusion
        )
        
        # Add specifications
        blog_specifications = []
        
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"Target audience: {audience_str}")
            
        if self.keywords:
            keywords_list, keywords_instruction = self.process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(keywords_instruction)
        
        # Add sample blog analysis if available
        sample_blog_instructions = self.analyze_sample_blog()
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        if blog_specifications:
            description += "\n\nADDITIONAL REQUIREMENTS:\n" + "\n".join(blog_specifications)
            
        expected_output = BlogWriterPrompts.get_writing_expected_output(
            self.topic, self.blog_type, self.length_min, self.length_max
        )
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.writer()
        )
    
    def editing_task(self, agents):
        description = BlogWriterPrompts.get_editing_prompt(
            self.topic, self.blog_type, self.length_min, self.length_max,
            self.introduction, self.table_of_content, self.faq, self.cta, self.conclusion
        )
            
        # Add verification requirements
        blog_specifications = []
        
        blog_specifications.append(f"Verify {self.blog_type} blog format is maintained throughout")
        blog_specifications.append(f"Ensure word count is exactly {self.length_min}-{self.length_max} words")
        blog_specifications.append("Verify comprehensive Sources section with all referenced URLs")
        
        if self.introduction:
            blog_specifications.append("Verify engaging ## Introduction section with research context")
        if self.table_of_content:
            blog_specifications.append("Ensure ## Table of Contents is accurate")
        if self.faq:
            blog_specifications.append("Verify ## FAQ section with research-backed answers")
        if self.cta:
            blog_specifications.append("Check ## Call to Action with actionable research-based recommendations")
        if self.conclusion:
            blog_specifications.append("Verify comprehensive ## Conclusion section summarizing key research insights")
            
        if self.target_audience:
            audience_str = ", ".join(self.target_audience)
            blog_specifications.append(f"Ensure content suits target audience: {audience_str}")
            
        if self.keywords:
            keywords_list, keywords_instruction = self.process_keywords_with_counts(self.keywords)
            if keywords_instruction:
                blog_specifications.append(f"Verify keyword usage: {keywords_instruction}")
        
        # Add sample blog analysis if available
        sample_blog_instructions = self.analyze_sample_blog()
        if sample_blog_instructions:
            description += sample_blog_instructions
            
        if blog_specifications:
            description += "\n\nVERIFICATION CHECKLIST:\n" + "\n".join(blog_specifications)
            
        expected_output = BlogWriterPrompts.get_editing_expected_output(
            self.topic, self.blog_type, self.length_min, self.length_max
        )
            
        return Task(
            description=description,
            expected_output=expected_output,
            agent=agents.editor()
        )
