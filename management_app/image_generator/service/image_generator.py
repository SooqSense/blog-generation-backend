import os
import requests
import boto3
import io
import time
from datetime import datetime
from openai import OpenAI
import fal_client
from .prompts import FLUX_AI_OPTIMIZATION_PROMPT

# Configure fal_client with API key
def _configure_fal_client():
    """Configure fal_client with API key from environment"""
    api_key = os.environ.get("FAL_KEY")
    if not api_key:
        raise ValueError("FAL_KEY not found in environment variables")
    fal_client.api_key = api_key

def optimize_image_prompt_for_flux(prompt, topic=None, keywords=None, image_type="content", image_number=1):
    """
    Optimize the image generation prompt specifically for FLUX AI
    
    Args:
        prompt (str): The original prompt for image generation
        topic (str, optional): The blog topic for context
        keywords (list, optional): Keywords to focus on in the image
        image_type (str): Type of image to generate (content, banner, etc.)
        image_number (int): The number of this image in a series
        
    Returns:
        str: Enhanced prompt optimized for FLUX AI
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
        
        # Use the imported system message for FLUX AI-style image generation
        system_message = FLUX_AI_OPTIMIZATION_PROMPT

        # Add variation instruction for multiple images
        variation_instruction = ""
        if image_number > 1:
            variation_instruction = f" This is image #{image_number} in a series, so create a unique artistic style or perspective while maintaining thematic consistency."
        
        # Construct the user message
        user_message = f"Optimize this prompt for FLUX AI image generation{topic_context}{keywords_context}: {prompt}{variation_instruction}"
        
        # Call the OpenAI API to optimize the prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=400
        )
        
        # Extract the optimized prompt
        optimized_prompt = response.choices[0].message.content.strip()
        
        # If the optimized prompt is empty or too short, fallback to original
        if not optimized_prompt or len(optimized_prompt) < 20:
            return prompt
            
        return optimized_prompt
        
    except Exception as e:
        print(f"Error optimizing image prompt for FLUX AI: {str(e)}")
        return prompt  # Return original prompt on error

def upload_image_to_s3(image_content, output_dir, filename):
    """
    Upload image to S3
    
    Args:
        image_content (bytes): The image content
        output_dir (str): Directory prefix for S3 storage
        filename (str): Name of the file
        
    Returns:
        str: S3 URL of uploaded image or local file path
    """
    try:
        s3_key = f"{output_dir}/{filename}"
        
        # Get S3 credentials from environment
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        region = os.environ.get("AWS_REGION")
        
        if not aws_access_key or not aws_secret_key or not bucket_name:
            # Fallback to local storage if no S3 credentials
            print(f"S3 credentials not found, saving image locally...")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(image_content)
            print(f"Image saved locally: {filepath}")
            return filepath
        else:
            try:
                # Initialize S3 client
                s3_client = boto3.client(
                    's3',
                    region_name=region or 'us-east-1',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
                
                # Upload to S3
                s3_client.upload_fileobj(
                    io.BytesIO(image_content),
                    bucket_name,
                    s3_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
                
                # Generate S3 URL
                region_part = f".{region}" if region and region != 'us-east-1' else ""
                final_image_url = f"https://{bucket_name}.s3{region_part}.amazonaws.com/{s3_key}"
                print(f"Image uploaded to S3: {final_image_url}")
                return final_image_url
                
            except Exception as s3_error:
                print(f"Error uploading image to S3: {str(s3_error)}")
                print(f"Falling back to local storage...")
                # Fallback to local storage
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_content)
                print(f"Image saved locally: {filepath}")
                return filepath
                
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return None

def generate_image_with_flux(prompt, size="1920x1080", output_dir="blog_images", topic=None, keywords=None, image_type="content", count=1):
    """
    Generate one or more images using FLUX AI via fal.ai API and upload to S3
    
    Args:
        prompt (str): The prompt for image generation
        size (str): The size of the image (default: "1920x1080")
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
        prompt = f"Create a professional, high-quality image about {fallback_topic}{keyword_focus} with intricate details and artistic composition."
        topic = fallback_topic

    count = max(1, min(count, 10))  # Ensure count is between 1 and 10
    
    # Configure fal_client
    try:
        _configure_fal_client()
    except ValueError as e:
        print(f"Error: {str(e)}")
        return [], 0, count

    images_data = []
    failed_generations = 0
    
    # Map size to fal.ai FLUX API image_size values
    image_size_map = {
        "1024x1024": "square_hd",
        "1024x1792": "portrait_16_9", 
        "1792x1024": "landscape_16_9",
        "1920x1080": "landscape_16_9",  # Full HD 16:9 format
        "512x512": "square",
        "768x1024": "portrait_4_3",
        "1024x768": "landscape_4_3"
    }
    
    image_size = image_size_map.get(size, "square_hd")
    
    # Generate images one by one
    for i in range(count):
        try:
            image_number = i + 1
            print(f"Generating FLUX AI image {image_number} of {count}...")
            
            # Optimize the prompt using the AI agent for FLUX AI
            optimized_prompt = optimize_image_prompt_for_flux(prompt, topic, keywords, image_type, image_number)
            print(f"Image {image_number} - Original prompt: {prompt}")
            print(f"Image {image_number} - FLUX AI-optimized prompt: {optimized_prompt}")

            # Generate image using fal.ai FLUX model
            result = fal_client.subscribe(
                "fal-ai/flux/dev",
                arguments={
                    "prompt": optimized_prompt,
                    "image_size": image_size,
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "num_images": 1,
                    "enable_safety_checker": True
                }
            )
            
            if not result or 'images' not in result or not result['images']:
                print(f"Error: No image returned from fal.ai for image {image_number}")
                failed_generations += 1
                continue
            
            # Get the generated image URL
            image_url = result['images'][0]['url']
            if not image_url:
                print(f"Error: No image URL returned for image {image_number}")
                failed_generations += 1
                continue
            
            # Download the image
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                print(f"Error: Failed to download FLUX AI image {image_number} from URL: {image_url}")
                failed_generations += 1
                continue
            
            # Prepare filename and upload to S3
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flux_ai_{timestamp}_img{image_number}.jpg"
            
            final_image_url = upload_image_to_s3(image_response.content, output_dir, filename)
            
            # Ensure we have a valid final_image_url
            if not final_image_url:
                print(f"Error: No valid image URL generated for FLUX AI image {image_number}")
                failed_generations += 1
                continue
            
            # Add successful generation to results
            images_data.append({
                'image_url': final_image_url,
                'enhanced_prompt': optimized_prompt,
                'image_number': image_number,
                'generation_type': 'flux_ai'
            })
            
            print(f"Successfully generated FLUX AI image {image_number}")
            
        except Exception as e:
            print(f"Error generating FLUX AI image {image_number}: {str(e)}")
            failed_generations += 1
            continue
    
    total_generated = len(images_data)
    print(f"FLUX AI generation complete: {total_generated} successful, {failed_generations} failed")
    
    return images_data, total_generated, failed_generations

def generate_image_with_flux_schnell(prompt, size="1920x1080", output_dir="blog_images", topic=None, keywords=None, image_type="content", count=1):
    """
    Generate one or more images using FLUX Schnell (faster model) via fal.ai API and upload to S3
    
    Args:
        prompt (str): The prompt for image generation
        size (str): The size of the image (default: "1920x1080")
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
        prompt = f"Create a professional, high-quality image about {fallback_topic}{keyword_focus} with intricate details and artistic composition."
        topic = fallback_topic

    count = max(1, min(count, 10))  # Ensure count is between 1 and 10
    
    # Configure fal_client
    try:
        _configure_fal_client()
    except ValueError as e:
        print(f"Error: {str(e)}")
        return [], 0, count

    images_data = []
    failed_generations = 0
    
    # Map size to fal.ai FLUX API image_size values
    image_size_map = {
        "1024x1024": "square_hd",
        "1024x1792": "portrait_16_9", 
        "1792x1024": "landscape_16_9",
        "1920x1080": "landscape_16_9",  # Full HD 16:9 format
        "512x512": "square",
        "768x1024": "portrait_4_3",
        "1024x768": "landscape_4_3"
    }
    
    image_size = image_size_map.get(size, "square_hd")
    
    # Generate images one by one
    for i in range(count):
        try:
            image_number = i + 1
            print(f"Generating FLUX Schnell image {image_number} of {count}...")
            
            # Optimize the prompt using the AI agent for FLUX AI
            optimized_prompt = optimize_image_prompt_for_flux(prompt, topic, keywords, image_type, image_number)
            print(f"Image {image_number} - Original prompt: {prompt}")
            print(f"Image {image_number} - FLUX Schnell-optimized prompt: {optimized_prompt}")

            # Generate image using fal.ai FLUX Schnell model
            result = fal_client.subscribe(
                "fal-ai/flux/schnell",
                arguments={
                    "prompt": optimized_prompt,
                    "image_size": image_size,
                    "num_inference_steps": 4,  # Schnell uses fewer steps for speed
                    "num_images": 1,
                    "enable_safety_checker": True
                }
            )
            
            if not result or 'images' not in result or not result['images']:
                print(f"Error: No image returned from fal.ai for image {image_number}")
                failed_generations += 1
                continue
            
            # Get the generated image URL
            image_url = result['images'][0]['url']
            if not image_url:
                print(f"Error: No image URL returned for image {image_number}")
                failed_generations += 1
                continue
                
            # Download the image
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                print(f"Error: Failed to download FLUX Schnell image {image_number} from URL: {image_url}")
                failed_generations += 1
                continue
            
            # Prepare filename and upload to S3
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flux_schnell_{timestamp}_img{image_number}.jpg"
            
            final_image_url = upload_image_to_s3(image_response.content, output_dir, filename)
            
            # Ensure we have a valid final_image_url
            if not final_image_url:
                print(f"Error: No valid image URL generated for FLUX Schnell image {image_number}")
                failed_generations += 1
                continue
            
            # Add successful generation to results
            images_data.append({
                'image_url': final_image_url,
                'enhanced_prompt': optimized_prompt,
                'image_number': image_number,
                'generation_type': 'flux_schnell'
            })
            
            print(f"Successfully generated FLUX Schnell image {image_number}")
            
        except Exception as e:
            print(f"Error generating FLUX Schnell image {image_number}: {str(e)}")
            failed_generations += 1
            continue
    
    total_generated = len(images_data)
    print(f"FLUX Schnell generation complete: {total_generated} successful, {failed_generations} failed")
    
    return images_data, total_generated, failed_generations

# Main image generation function (backward compatibility wrapper)
def generate_image(prompt, size="1920x1080", output_dir="blog_images", topic=None, image_type="content", count=1, keywords=None, generation_method="flux"):
    """
    Generate images using FLUX AI models via fal.ai (backward compatibility wrapper)
    
    Args:
        prompt (str): The prompt for image generation
        size (str): The size of the image (default: "1920x1080")
        output_dir (str): Directory to save the image
        topic (str, optional): The blog topic for context
        image_type (str): Type of image to generate
        count (int): Number of images to generate (1-10)
        keywords (list, optional): Keywords to focus on in the image
        generation_method (str): Generation method to use ("flux" or "flux_schnell")
        
    Returns:
        tuple: (images_data, total_generated, failed_generations)
    """
    # Validate generation method
    if generation_method not in ["flux", "flux_schnell"]:
        print(f"Warning: Invalid generation method '{generation_method}'. Defaulting to 'flux'.")
        generation_method = "flux"
    
    # Call the appropriate generation function
    if generation_method == "flux_schnell":
        return generate_image_with_flux_schnell(prompt, size, output_dir, topic, keywords, image_type, count)
    else:  # Default to flux
        return generate_image_with_flux(prompt, size, output_dir, topic, keywords, image_type, count)