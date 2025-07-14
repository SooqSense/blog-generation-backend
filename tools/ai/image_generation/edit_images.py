import os
import requests
import boto3
import io
import time
import base64
from datetime import datetime
from openai import OpenAI
from .prompts import FLUX_AI_EDITING_PROMPT

def optimize_image_editing_prompt(prompt, keywords=None):
    """
    Optimize the image editing prompt specifically for FLUX AI editing
    
    Args:
        prompt (str): The original editing prompt
        keywords (str, optional): Keywords to focus on in the editing
        
    Returns:
        str: Enhanced prompt optimized for FLUX AI editing
    """
    try:
        # Check for API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return prompt  # Return original prompt if no API key
            
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Context to provide to the optimization agent
        keywords_context = f" focusing on these keywords: {keywords}" if keywords and keywords.strip() else ""
        
        # Use the imported system message for FLUX AI editing
        system_message = FLUX_AI_EDITING_PROMPT
        
        # Construct the user message
        user_message = f"Optimize this prompt for FLUX AI image editing{keywords_context}: {prompt}"
        
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
        print(f"Error optimizing image editing prompt: {str(e)}")
        return prompt  # Return original prompt on error

def convert_image_to_base64(image_file):
    """
    Convert uploaded image file to base64 string
    
    Args:
        image_file: Django UploadedFile object
        
    Returns:
        str: Base64 encoded image string
    """
    try:
        # Read the image file
        image_content = image_file.read()
        
        # Convert to base64
        base64_string = base64.b64encode(image_content).decode('utf-8')
        
        return base64_string
        
    except Exception as e:
        print(f"Error converting image to base64: {str(e)}")
        return None

def edit_image_with_flux(prompt, image_base64, keywords=None, output_dir="edited_images"):
    """
    Edit an image using FLUX AI API
    
    Args:
        prompt (str): The editing prompt
        image_base64 (str): Base64 encoded original image
        keywords (str, optional): Keywords to focus on in the editing
        output_dir (str): Directory to save the edited image
        
    Returns:
        tuple: (success, edited_image_url, enhanced_prompt, error_message)
    """
    # Check for API key
    api_key = os.environ.get("BFL_API_KEY")
    if not api_key:
        return False, None, prompt, "BFL_API_KEY not found in environment variables"

    try:
        print(f"Starting FLUX AI image editing...")
        
        # Optimize the editing prompt
        enhanced_prompt = optimize_image_editing_prompt(prompt, keywords)
        print(f"Original prompt: {prompt}")
        print(f"Enhanced prompt: {enhanced_prompt}")

        # Prepare request headers
        headers = {
            'accept': 'application/json',
            'x-key': api_key,
            'Content-Type': 'application/json'
        }
        
        # Prepare request data for image editing
        request_data = {
            'prompt': enhanced_prompt,
            'input_image': image_base64,
            'output_format': 'jpeg',
            'safety_tolerance': 2
        }
        
        # Make request to FLUX AI API for image editing
        response = requests.post(
            'https://api.bfl.ai/v1/flux-kontext-pro',
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        if response.status_code != 200:
            error_msg = f"FLUX AI API returned status {response.status_code}: {response.text}"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg
            
        response_data = response.json()
        request_id = response_data.get('id')
        polling_url = response_data.get('polling_url')
        
        if not request_id or not polling_url:
            error_msg = "No request ID or polling URL returned from FLUX AI API"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg
        
        # Poll for result
        print(f"Polling for FLUX AI editing result...")
        max_polls = 120  # Maximum 2 minutes (60 seconds with 0.5s interval)
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
                
                print(f"FLUX AI editing status: {status}")
                
                if status == 'Ready':
                    edited_image_url = poll_data.get('result', {}).get('sample')
                    if edited_image_url:
                        break
                    else:
                        error_msg = "No edited image URL in ready response"
                        print(f"Error: {error_msg}")
                        return False, None, enhanced_prompt, error_msg
                elif status in ['Error', 'Failed']:
                    error_msg = f"FLUX AI editing failed: {poll_data}"
                    print(f"Error: {error_msg}")
                    return False, None, enhanced_prompt, error_msg
                
            except Exception as poll_error:
                print(f"Error polling FLUX AI result: {str(poll_error)}")
                continue
        
        if poll_count >= max_polls:
            error_msg = "Timeout waiting for FLUX AI editing result"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg
        
        if status != 'Ready' or not edited_image_url:
            error_msg = "Failed to get ready edited image"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg
        
        # Download the edited image
        image_response = requests.get(edited_image_url, timeout=30)
        if image_response.status_code != 200:
            error_msg = f"Failed to download edited image from URL: {edited_image_url}"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg
        
        # Upload to S3
        final_image_url = upload_edited_image_to_s3(image_response.content, output_dir)
        
        if not final_image_url:
            error_msg = "Failed to upload edited image to S3"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg
        
        print(f"Successfully edited image and uploaded to: {final_image_url}")
        return True, final_image_url, enhanced_prompt, None
        
    except Exception as e:
        error_msg = f"Error in FLUX AI image editing: {str(e)}"
        print(error_msg)
        return False, None, prompt, error_msg

def upload_edited_image_to_s3(image_content, output_dir):
    """
    Upload edited image to S3
    
    Args:
        image_content (bytes): The edited image content
        output_dir (str): Directory prefix for S3 storage
        
    Returns:
        str: S3 URL of uploaded image or local file path
    """
    try:
        # Prepare S3 upload
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"edited_{timestamp}.jpg"
        s3_key = f"{output_dir}/{filename}"
        
        # Get S3 credentials from environment
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        bucket_name = os.environ.get("S3_BUCKET_NAME")
        region = os.environ.get("AWS_REGION")
        
        if not aws_access_key or not aws_secret_key or not bucket_name:
            # Fallback to local storage if no S3 credentials
            print(f"S3 credentials not found, saving edited image locally...")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(image_content)
            print(f"Edited image saved locally: {filepath}")
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
                print(f"Edited image uploaded to S3: {final_image_url}")
                return final_image_url
                
            except Exception as s3_error:
                print(f"Error uploading edited image to S3: {str(s3_error)}")
                print(f"Falling back to local storage...")
                # Fallback to local storage
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(image_content)
                print(f"Edited image saved locally: {filepath}")
                return filepath
                
    except Exception as e:
        print(f"Error uploading edited image: {str(e)}")
        return None
