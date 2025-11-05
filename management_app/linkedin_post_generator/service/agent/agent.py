import re
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings

from management_app.linkedin_post_generator.service.prompts.prompts import (
    LINKEDIN_ROLE,
    LINKEDIN_GOAL,
    LINKEDIN_BACKSTORY,
    build_task_description,
    build_expected_output,
    PREFIXES,
    EXPLANATION_PATTERNS,
)

try:
    from management_app.langsmith_integration.langsmith_integration import (
        log_cost, trace_linkedin_generator
    )
    LANGSMITH_AVAILABLE = True
except ImportError:
    def log_cost(operation, model, tokens_used=None, cost_estimate=None, additional_data=None):
        pass
    def trace_linkedin_generator(operation, metadata=None):
        def decorator(func):
            return func
        return decorator
    LANGSMITH_AVAILABLE = False


def create_linkedin_post_writer_agent(llm) -> Agent:
    return Agent(
        role=LINKEDIN_ROLE,
        goal=LINKEDIN_GOAL,
        backstory=LINKEDIN_BACKSTORY,
        verbose=True,
        llm=llm,
        allow_delegation=False,
    )


def create_linkedin_generation_task(topic, keywords, writer_agent: Agent) -> Task:
    return Task(
        description=build_task_description(topic, keywords),
        expected_output=build_expected_output(topic),
        agent=writer_agent,
    )

def _build_llm(use_custom_llm: bool):
    if use_custom_llm:
        gemini_api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        if not gemini_api_key:
            raise ValueError("GOOGLE_API_KEY not found in Django settings for custom LLM.")
        return ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=gemini_api_key,
            temperature=0.7,
        )
    openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in Django settings for default LLM.")
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        api_key=openai_api_key,
        temperature=0.7
    )


@trace_linkedin_generator("generate_post", metadata={"type": "content_creation", "platform": "linkedin"})
def generate_linkedin_post(topic: str, keywords=None, use_custom_llm: bool = False):
    if not topic:
        raise ValueError("Topic must be provided for LinkedIn post generation.")

    llm = _build_llm(use_custom_llm)

    # Cost estimate (if available)
    if LANGSMITH_AVAILABLE:
        model_name = "gpt-3.5-turbo" if not use_custom_llm else "gemini-pro"
        estimated_tokens = 250
        estimated_cost = estimated_tokens * 0.000001 if "gpt-3.5-turbo" in model_name else estimated_tokens * 0.000005
        log_cost(
            operation="linkedin_post_generation_start",
            model=model_name,
            tokens_used=int(estimated_tokens),
            cost_estimate=estimated_cost,
            additional_data={
                "topic": topic,
                "keywords": keywords or [],
                "keywords_count": len(keywords) if keywords else 0,
                "estimated_tokens": int(estimated_tokens),
            },
        )

    # Build agent and task
    writer_agent = create_linkedin_post_writer_agent(llm)
    generation_task = create_linkedin_generation_task(topic, keywords or [], writer_agent)

    # Run crew
    linkedin_crew = Crew(
        agents=[writer_agent],
        tasks=[generation_task],
        process=Process.sequential,
        verbose=True,
    )

    # Increase temperature during generation for variety
    if hasattr(llm, 'temperature'):
        original_temp = llm.temperature
        llm.temperature = 0.8

    import random
    post_content_raw = str(
        linkedin_crew.kickoff(
            inputs={
                "topic": topic,
                "variation_key": str(random.randint(1000, 9999)),
            }
        )
    ).strip()

    if hasattr(llm, 'temperature'):
        llm.temperature = original_temp

    # Cleanup
    if post_content_raw:
        for prefix in PREFIXES:
            if post_content_raw.startswith(prefix):
                post_content_raw = post_content_raw[len(prefix):].strip()

        post_content_raw = re.sub(r'^\s*\[.*?\]\s*', '', post_content_raw, flags=re.MULTILINE)
        post_content_raw = re.sub(r'^\s*Title:.*$', '', post_content_raw, flags=re.MULTILINE)
        post_content_raw = re.sub(r'^\s*Paragraph \d+:?\s*', '', post_content_raw, flags=re.MULTILINE)
        post_content_raw = re.sub(r'^\s*Introduction:?\s*', '', post_content_raw, flags=re.MULTILINE)
        post_content_raw = re.sub(r'^\s*Conclusion:?\s*', '', post_content_raw, flags=re.MULTILINE)
        post_content_raw = re.sub(r'^\s*Hashtags:?\s*', '', post_content_raw, flags=re.MULTILINE)

        post_content_raw = re.sub(r'^\s*[-•*]\s+', '', post_content_raw, flags=re.MULTILINE)
        post_content_raw = re.sub(r'^\s*\d+[.)\]]\s+', '', post_content_raw, flags=re.MULTILINE)

        for pattern in EXPLANATION_PATTERNS:
            post_content_raw = re.sub(pattern, '', post_content_raw, flags=re.DOTALL)

        lines = post_content_raw.split('\n')
        processed_lines = []
        for line in lines:
            if any(word.startswith('#') for word in line.split()):
                words = []
                for word in line.split():
                    words.append(word.lower() if word.startswith('#') else word)
                processed_lines.append(' '.join(words))
            else:
                processed_lines.append(line)

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

    if LANGSMITH_AVAILABLE and post_content:
        actual_char_count = len(post_content)
        model_name = "gpt-3.5-turbo" if not use_custom_llm else "gemini-pro"
        estimated_tokens = actual_char_count // 4
        final_cost_estimate = estimated_tokens * 0.000001 if "gpt-3.5-turbo" in model_name else estimated_tokens * 0.000005
        log_cost(
            operation="linkedin_post_generation_complete",
            model=model_name,
            tokens_used=int(estimated_tokens),
            cost_estimate=final_cost_estimate,
            additional_data={
                "topic": topic,
                "keywords": keywords or [],
                "actual_char_count": actual_char_count,
                "post_contains_hashtags": '#' in post_content,
                "estimated_tokens": int(estimated_tokens),
                "success": True,
            },
        )

    return post_content, None


