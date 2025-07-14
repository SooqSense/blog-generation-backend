import os
import requests
import boto3
import io
import time
import json
from datetime import datetime
from openai import OpenAI
from .prompts import SORA_OPTIMIZATION_PROMPT, FLUX_AI_OPTIMIZATION_PROMPT

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
        
        # Use the imported system message for Sora-style image generation
        system_message = SORA_OPTIMIZATION_PROMPT

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

def generate_image_with_flux(prompt, size="1024x1024", output_dir="blog_images", topic=None, keywords=None, image_type="content", count=1):
    """
    Generate one or more images using FLUX AI API and upload to S3
    
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
        prompt = f"Create a professional, high-quality image about {fallback_topic}{keyword_focus} with intricate details and artistic composition."
        topic = fallback_topic

    count = max(1, min(count, 10))  # Ensure count is between 1 and 10
    
    # Check for API key
    api_key = os.environ.get("BFL_API_KEY")
    if not api_key:
        print("Error: BFL_API_KEY not found in environment variables")
        return [], 0, count

    images_data = []
    failed_generations = 0
    
    # Generate images one by one
    for i in range(count):
        try:
            image_number = i + 1
            print(f"Generating FLUX AI image {image_number} of {count}...")
            
            # Optimize the prompt using the AI agent for FLUX AI
            optimized_prompt = optimize_image_prompt_for_flux(prompt, topic, keywords, image_type, image_number)
            print(f"Image {image_number} - Original prompt: {prompt}")
            print(f"Image {image_number} - FLUX AI-optimized prompt: {optimized_prompt}")

            # Prepare request headers
            headers = {
                'accept': 'application/json',
                'x-key': api_key,
                'Content-Type': 'application/json'
            }
            
            # Prepare request data
            request_data = {
                'prompt': optimized_prompt,
                'aspect_ratio': '1:1',  # Convert size to aspect ratio
                'output_format': 'jpeg',
                'safety_tolerance': 2
            }
            
            # Convert size to aspect ratio if needed
            if size == "1024x1024":
                request_data['aspect_ratio'] = '1:1'
            elif size == "1024x1792":
                request_data['aspect_ratio'] = '9:16'
            elif size == "1792x1024":
                request_data['aspect_ratio'] = '16:9'
            
            # Make request to FLUX AI API
            response = requests.post(
                'https://api.bfl.ai/v1/flux-kontext-pro',
                headers=headers,
                json=request_data,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error: FLUX AI API returned status {response.status_code}: {response.text}")
                failed_generations += 1
                continue
                
            response_data = response.json()
            request_id = response_data.get('id')
            polling_url = response_data.get('polling_url')
            
            if not request_id or not polling_url:
                print(f"Error: No request ID or polling URL returned from FLUX AI API for image {image_number}")
                failed_generations += 1
                continue
            
            # Poll for result
            print(f"Polling for FLUX AI image {image_number} result...")
            max_polls = 60  # Maximum 60 polls (30 seconds with 0.5s interval)
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(0.5)
                poll_count += 1
                
                try:
                    poll_response = requests.get(
                        polling_url,
                        headers={'accept': 'application/json', 'x-key': api_key},
                        timeout=10
                    )
                    
                    if poll_response.status_code != 200:
                        print(f"Error polling FLUX AI result: {poll_response.status_code}")
                        continue
                    
                    poll_data = poll_response.json()
                    status = poll_data.get('status')
                    
                    print(f"FLUX AI image {image_number} status: {status}")
                    
                    if status == 'Ready':
                        image_url = poll_data.get('result', {}).get('sample')
                        if image_url:
                            break
                        else:
                            print(f"Error: No image URL in ready response for image {image_number}")
                            failed_generations += 1
                            break
                    elif status in ['Error', 'Failed']:
                        print(f"FLUX AI generation failed for image {image_number}: {poll_data}")
                        failed_generations += 1
                        break
                    
                except Exception as poll_error:
                    print(f"Error polling FLUX AI result: {str(poll_error)}")
                    continue
            
            if poll_count >= max_polls:
                print(f"Timeout waiting for FLUX AI image {image_number}")
                failed_generations += 1
                continue
            
            if status != 'Ready' or not image_url:
                print(f"Failed to get ready image for image {image_number}")
                failed_generations += 1
                continue
            
            # Download the image
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                print(f"Error: Failed to download FLUX AI image {image_number} from URL: {image_url}")
                failed_generations += 1
                continue
            
            # Prepare S3 upload
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flux_ai_{timestamp}_img{image_number}.jpg"
            s3_key = f"{output_dir}/{filename}"
            
            # Get S3 credentials from environment
            aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
            bucket_name = os.environ.get("S3_BUCKET_NAME")
            region = os.environ.get("AWS_REGION")
            
            final_image_url = None
            
            if not aws_access_key or not aws_secret_key or not bucket_name:
                # Fallback to local storage if no S3 credentials
                print(f"S3 credentials not found, saving FLUX AI image {image_number} locally...")
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_response.content)
                final_image_url = filepath
                print(f"FLUX AI image saved locally: {filepath}")
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
                        io.BytesIO(image_response.content),
                        bucket_name,
                        s3_key,
                        ExtraArgs={'ContentType': 'image/jpeg'}
                    )
                    
                    # Generate S3 URL
                    region_part = f".{region}" if region and region != 'us-east-1' else ""
                    final_image_url = f"https://{bucket_name}.s3{region_part}.amazonaws.com/{s3_key}"
                    print(f"FLUX AI image uploaded to S3: {final_image_url}")
                    
                except Exception as s3_error:
                    print(f"Error uploading FLUX AI image {image_number} to S3: {str(s3_error)}")
                    print(f"Falling back to local storage for image {image_number}...")
                    # Fallback to local storage
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(image_response.content)
                    final_image_url = filepath
                    print(f"FLUX AI image saved locally: {filepath}")
            
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
            if not image_url:
                print(f"Error: No image URL returned from OpenAI API for image {image_number}")
                failed_generations += 1
                continue
                
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                print(f"Error: Failed to download image {image_number} from URL: {image_url}")
                failed_generations += 1
                continue
            
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
            
            if not aws_access_key or not aws_secret_key or not bucket_name:
                # Fallback to local storage if no S3 credentials
                print(f"S3 credentials not found, saving image {image_number} locally...")
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_response.content)
                final_image_url = filepath
                print(f"Image saved locally: {filepath}")
            else:
                try:
                    # Initialize S3 client
                    s3_client = boto3.client(
                        's3',
                        region_name=region or 'us-east-1',  # Default region if not specified
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
                    region_part = f".{region}" if region and region != 'us-east-1' else ""
                    final_image_url = f"https://{bucket_name}.s3{region_part}.amazonaws.com/{s3_key}"
                    print(f"Image uploaded to S3: {final_image_url}")
                    
                except Exception as s3_error:
                    print(f"Error uploading to S3 for image {image_number}: {str(s3_error)}")
                    print(f"Falling back to local storage for image {image_number}...")
                    # Fallback to local storage
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(image_response.content)
                    final_image_url = filepath
                    print(f"Image saved locally: {filepath}")
            
            # Ensure we have a valid final_image_url
            if not final_image_url:
                print(f"Error: No valid image URL generated for image {image_number}")
                failed_generations += 1
                continue
            
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

# Backward compatibility - keep the original function name but support both generation methods
def generate_image(prompt, size="1024x1024", output_dir="blog_images", topic=None, image_type="content", count=1, keywords=None, generation_method="sora"):
    """
    Generate images using either Sora-style or FLUX AI generation (backward compatibility wrapper)
    
    Args:
        prompt (str): The prompt for image generation
        size (str): The size of the image (default: "1024x1024")
        output_dir (str): Directory to save the image
        topic (str, optional): The blog topic for context
        image_type (str): Type of image to generate
        count (int): Number of images to generate (1-10)
        keywords (list, optional): Keywords to focus on in the image
        generation_method (str): Generation method to use ("sora" or "flux")
        
    Returns:
        tuple: (images_data, total_generated, failed_generations)
    """
    # Validate generation method
    if generation_method not in ["sora", "flux"]:
        print(f"Warning: Invalid generation method '{generation_method}'. Defaulting to 'sora'.")
        generation_method = "sora"
    
    # Call the appropriate generation function
    if generation_method == "flux":
        return generate_image_with_flux(prompt, size, output_dir, topic, keywords, image_type, count)
    else:  # Default to sora
        return generate_image_with_sora(prompt, size, output_dir, topic, keywords, image_type, count)