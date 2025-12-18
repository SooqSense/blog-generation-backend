import json
from ..agents.contextual_image_agent import ContextualImagePromptAgent
from management_app.image_generator.service.image_generator import (
    generate_image_with_flux,
    generate_image_with_flux_schnell,
)


def generate_section_specific_images(
    topic,
    blog_type,
    blog_content,
    generation_method="flux",
    output_dir="blog_images",
    use_custom_llm=False,
):
    """
    Generate images for a single blog section using contextual prompt analysis.
    Returns dict with section image metadata.
    """
    contextual_agent = ContextualImagePromptAgent(use_custom_llm=use_custom_llm)
    prompt_data = contextual_agent.generate_prompt(
        topic=topic,
        section_title="banner",  # single section mode
        section_content=blog_content,
        blog_type=blog_type,
    )

    prompt = prompt_data["prompt"]

    print(f"🎨 Generating image with FLUX for section: {topic}")
    if generation_method == "flux_schnell":
        images_data, total_generated, failed_generations = generate_image_with_flux_schnell(
            prompt=prompt,
            size="1920x1080",
            output_dir=f"{output_dir}/banner",
            topic=topic,
            keywords=None,
            image_type="banner",
            count=1,
        )
    else:
        images_data, total_generated, failed_generations = generate_image_with_flux(
            prompt=prompt,
            size="1920x1080",
            output_dir=f"{output_dir}/banner",
            topic=topic,
            keywords=None,
            image_type="banner",
            count=1,
        )

    if not images_data:
        print("⚠️ Flux image generation failed.")
        return {}

    image_data = images_data[0]
    return {
        "banner": {
            "image_url": image_data.get("image_url"),
            "prompt": prompt,
            "enhanced_prompt": image_data.get("enhanced_prompt", prompt),
            "generation_method": generation_method,
        }
    }


def embed_images_in_blog_content(blog_content, section_images):
    """
    Embed generated image(s) at the end of section content.
    """
    lines = blog_content.strip().split("\n")
    result = list(lines)
    for section, data in section_images.items():
        image_url = data.get("image_url")
        if image_url:
            result.append("")
            result.append(f"![{section.title()} Image]({image_url})")
            result.append("")
    return "\n".join(result)
