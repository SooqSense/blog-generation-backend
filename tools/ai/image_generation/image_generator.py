import os
import requests
import boto3
import io
from datetime import datetime
from openai import OpenAI

def optimize_image_prompt_for_sora(prompt, topic=None, keywords=None, image_type="content", image_number=1):
    """
    Optimize the image generation prompt specifically for Sora AI
    
    Args:
        prompt (str): The original prompt for image generation
        topic (str, optional): The blog topic for context
        keywords (list, optional): Keywords to focus on in the image
        image_type (str): Type of image to generate (content, banner, etc.)
        image_number (int): The number of this image in a series
        
    Returns:
        str: Enhanced prompt optimized for Sora AI
    """
    try:
        # Check for API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return prompt  # Return original prompt if no API key
            
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Context to provide to the optimization agent
        topic_context = f" about {topic}" if topic else ""
        keywords_context = f" focusing on these keywords: {', '.join(keywords)}" if keywords else ""
        
        # Create specialized system message for Sora-style image generation
        system_message = """You are an expert prompt engineer for Sora AI video/image generation. 
Your job is to enhance prompts to create clean, professional, and visually appealing images that match Sora's capabilities.

CRITICAL REQUIREMENTS FOR SORA PROMPTS:
1. Create CLEAN and PROFESSIONAL images - NO messy or cluttered visuals
2. Focus on REALISTIC and CINEMATIC quality that Sora excels at
3. Avoid infographics, charts, or data visualization elements
4. Emphasize VISUAL STORYTELLING and atmospheric scenes
5. Use descriptive language for lighting, composition, and mood
6. Focus on the KEYWORDS provided to ensure relevance
7. Create prompts for high-quality, photorealistic or artistic images
8. Avoid text overlays or graphic design elements
9. Emphasize natural scenes, professional environments, or artistic compositions
10. Use cinematic terminology (wide shot, close-up, dramatic lighting, etc.)

SORA STYLE GUIDELINES:
- Use cinematic language: "wide shot", "close-up", "dramatic lighting", "golden hour"
- Focus on atmosphere and mood
- Describe camera movements if applicable: "slow zoom", "pan across", "tracking shot"
- Emphasize realistic textures and materials
- Use professional photography/videography terms
- Create scenes that tell a story visually
KEYWORD INTEGRATION:
- Seamlessly integrate the provided keywords into visual elements
- Make keywords the focal point of the scene
- Ensure keywords are represented through objects, environments, or actions
- Create visual metaphors for abstract keywords
- Avoid cartoonish or unrealistic images

OUTPUT FORMAT:
Provide a single, enhanced prompt that is 2-3 sentences long, focusing on visual elements, atmosphere, and keyword integration."""

        # Add variation instruction for multiple images
        variation_instruction = ""
        if image_number > 1:
            variation_instruction = f" This is image #{image_number} in a series, so create a unique visual angle or perspective while maintaining thematic consistency."
        
        # Construct the user message
        user_message = f"Optimize this prompt for Sora AI image generation{topic_context}{keywords_context}: {prompt}{variation_instruction}"
        
        # Call the OpenAI API to optimize the prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        # Extract the optimized prompt
        optimized_prompt = response.choices[0].message.content.strip()
        
        # If the optimized prompt is empty or too short, fallback to original
        if not optimized_prompt or len(optimized_prompt) < 20:
            return prompt
            
        return optimized_prompt
        
    except Exception as e:
        print(f"Error optimizing image prompt for Sora: {str(e)}")
        return prompt  # Return original prompt on error

def generate_image_with_sora(prompt, size="1024x1024", output_dir="blog_images", topic=None, keywords=None, image_type="content", count=1):
    """
    Generate one or more images using Sora AI (via OpenAI API) and upload to S3
    
    Args:
        prompt (str): The prompt for image generation
        size (str): The size of the image (default: "1024x1024")
        output_dir (str): Directory to save the image (now only used as a prefix in S3)
        topic (str, optional): The blog topic for prompt optimization context
        keywords (list, optional): Keywords to focus on in the image
        image_type (str): Type of image to generate (content, banner, etc.)
        count (int): Number of images to generate (1-10)
        
    Returns:
        tuple: (images_data, total_generated, failed_generations) where:
               - images_data is a list of dicts with 'image_url', 'enhanced_prompt', 'image_number'
               - total_generated is the number of successfully generated images
               - failed_generations is the number of failed attempts
    """
    # Validate inputs
    if not prompt or not prompt.strip():
        fallback_topic = topic if topic else "Professional content"
        keyword_focus = f" featuring {', '.join(keywords[:3])}" if keywords else ""
        prompt = f"Create a professional, cinematic image about {fallback_topic}{keyword_focus} with clean composition and dramatic lighting."
        topic = fallback_topic

    count = max(1, min(count, 10))  # Ensure count is between 1 and 10
    
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return [], 0, count

    images_data = []
    failed_generations = 0
    
    # Generate images one by one
    for i in range(count):
        try:
            image_number = i + 1
            print(f"Generating Sora-style image {image_number} of {count}...")
            
            # Optimize the prompt using the AI agent for Sora
            optimized_prompt = optimize_image_prompt_for_sora(prompt, topic, keywords, image_type, image_number)
            print(f"Image {image_number} - Original prompt: {prompt}")
            print(f"Image {image_number} - Sora-optimized prompt: {optimized_prompt}")

            # Initialize OpenAI client and generate image
            # Note: Currently using DALL-E 3 as Sora API might not be available yet
            # This can be updated when Sora API becomes available
            client = OpenAI(api_key=api_key)
            
            # For now, we'll use DALL-E 3 with Sora-style prompts
            # When Sora API is available, this section can be updated
            response = client.images.generate(
                model="dall-e-3",  # Will be updated to "sora" when available
                prompt=optimized_prompt,
                size=size,
                quality="hd",  # Use HD quality for better results
                style="natural",  # Use natural style for more realistic images
                n=1,
            )
            
            # Download the image
            image_url = response.data[0].url
            image_response = requests.get(image_url)
            
            # Prepare S3 upload
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sora_style_{timestamp}_img{image_number}.png"
            s3_key = f"{output_dir}/{filename}"
            
            # Get S3 credentials from environment
            aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
            bucket_name = os.environ.get("S3_BUCKET_NAME")
            region = os.environ.get("AWS_REGION")
            
            final_image_url = None
            
            if not aws_access_key or not aws_secret_key:
                # Fallback to local storage if no S3 credentials
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_response.content)
                final_image_url = filepath
                print(f"Image saved locally: {filepath}")
            else:
                # Initialize S3 client
                s3_client = boto3.client(
                    's3',
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
                
                # Upload to S3
                s3_client.upload_fileobj(
                    io.BytesIO(image_response.content),
                    bucket_name,
                    s3_key,
                    ExtraArgs={'ContentType': 'image/png'}
                )
                
                # Generate S3 URL
                final_image_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
                print(f"Image uploaded to S3: {final_image_url}")
            
            # Add successful generation to results
            images_data.append({
                'image_url': final_image_url,
                'enhanced_prompt': optimized_prompt,
                'image_number': image_number,
                'generation_type': 'sora_style'
            })
            
            print(f"Successfully generated Sora-style image {image_number}")
            
        except Exception as e:
            print(f"Error generating Sora-style image {image_number}: {str(e)}")
            failed_generations += 1
            continue
    
    total_generated = len(images_data)
    print(f"Sora-style generation complete: {total_generated} successful, {failed_generations} failed")
    
    return images_data, total_generated, failed_generations

# Backward compatibility - keep the original function name but use Sora-style generation
def generate_image(prompt, size="1024x1024", output_dir="blog_images", topic=None, image_type="content", count=1, keywords=None):
    """
    Generate images using Sora-style prompts (backward compatibility wrapper)
    
    Args:
        prompt (str): The prompt for image generation
        size (str): The size of the image (default: "1024x1024")
        output_dir (str): Directory to save the image
        topic (str, optional): The blog topic for context
        image_type (str): Type of image to generate
        count (int): Number of images to generate (1-10)
        keywords (list, optional): Keywords to focus on in the image
        
    Returns:
        tuple: (images_data, total_generated, failed_generations)
    """
    return generate_image_with_sora(prompt, size, output_dir, topic, keywords, image_type, count)