import os
import requests
import boto3
import io
import base64
from datetime import datetime
from openai import OpenAI
import fal_client
from django.conf import settings  # ✅ use Django settings instead of os.environ
from .prompts import FLUX_AI_EDITING_PROMPT


# Configure fal_client with API key
def _configure_fal_client():
    """Configure fal_client with API key from Django settings"""
    api_key = getattr(settings, "FAL_KEY", None)
    if not api_key:
        raise ValueError("FAL_KEY not found in Django settings")
    fal_client.api_key = api_key


def optimize_image_editing_prompt(prompt, keywords=None):
    """
    Optimize the image editing prompt specifically for FLUX AI editing
    """
    try:
        # ✅ Get API key from Django settings
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            return prompt  # Return original prompt if no API key

        client = OpenAI(api_key=api_key)

        keywords_context = f" focusing on these keywords: {keywords}" if keywords and keywords.strip() else ""
        system_message = FLUX_AI_EDITING_PROMPT
        user_message = f"Optimize this prompt for FLUX AI image editing{keywords_context}: {prompt}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=300,
        )

        optimized_prompt = response.choices[0].message.content.strip()
        if not optimized_prompt or len(optimized_prompt) < 20:
            return prompt

        return optimized_prompt

    except Exception as e:
        print(f"Error optimizing image editing prompt: {str(e)}")
        return prompt


def convert_image_to_base64(image_file):
    """Convert uploaded image file to base64 string"""
    try:
        image_content = image_file.read()
        base64_string = base64.b64encode(image_content).decode("utf-8")
        return base64_string
    except Exception as e:
        print(f"Error converting image to base64: {str(e)}")
        return None


def upload_image_from_url(image_url, output_dir):
    """Download image from URL and upload to S3"""
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code != 200:
            print(f"Error: Failed to download image from URL: {image_url}")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"edited_{timestamp}.jpg"
        return upload_edited_image_to_s3(response.content, output_dir, filename)
    except Exception as e:
        print(f"Error downloading and uploading image from URL: {str(e)}")
        return None


def edit_image_with_flux(prompt, image_base64, keywords=None, output_dir="edited_images", strength=0.8):
    """
    Edit an image using FLUX AI image-to-image transformation via fal.ai API
    """
    try:
        _configure_fal_client()
    except ValueError as e:
        return False, None, prompt, str(e)

    try:
        print(f"Starting FLUX AI image editing via fal.ai...")

        enhanced_prompt = optimize_image_editing_prompt(prompt, keywords)
        print(f"Original prompt: {prompt}")
        print(f"Enhanced prompt: {enhanced_prompt}")

        strength = max(0.1, min(1.0, strength))
        image_data_url = f"data:image/jpeg;base64,{image_base64}"

        result = fal_client.subscribe(
            "fal-ai/flux/dev/image-to-image",
            arguments={
                "prompt": enhanced_prompt,
                "image_url": image_data_url,
                "strength": strength,
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_images": 1,
                "enable_safety_checker": True,
            },
        )

        if not result or "images" not in result or not result["images"]:
            error_msg = "No edited image returned from fal.ai FLUX model"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg

        edited_image_url = result["images"][0]["url"]
        if not edited_image_url:
            error_msg = "No edited image URL returned from fal.ai"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg

        final_image_url = upload_image_from_url(edited_image_url, output_dir)
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


def upload_edited_image_to_s3(image_content, output_dir, filename=None):
    """Upload edited image to S3 with improved error handling"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"edited_{timestamp}.jpg"

    s3_key = f"{output_dir}/{filename}"

    # ✅ Get S3 credentials directly from Django settings
    aws_access_key = settings.AWS_ACCESS_KEY_ID
    aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
    bucket_name = settings.S3_BUCKET_NAME
    region = settings.AWS_REGION

    # Debug logging
    print(f"🔍 S3 Debug Info (Edited Image):")
    print(f"   - Bucket: {bucket_name}")
    print(f"   - Region: {region}")
    print(f"   - Access Key: {'*' * 8}{aws_access_key[-4:] if aws_access_key else 'None'}")
    print(f"   - Secret Key: {'*' * 8}{aws_secret_key[-4:] if aws_secret_key else 'None'}")
    print(f"   - S3 Key: {s3_key}")

    # ✅ REQUIRE S3 credentials - no local fallback
    if not aws_access_key or not aws_secret_key or not bucket_name:
        error_msg = "S3 credentials not configured. Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME in Django settings."
        print(f"❌ ERROR: {error_msg}")
        raise ValueError(error_msg)

    # Create S3 client
    s3_client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
    )

    # Upload edited image to S3 directly with improved error handling
    try:
        s3_client.upload_fileobj(
            io.BytesIO(image_content),
            bucket_name,
            s3_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
        region_part = f".{region}" if region and region != "us-east-1" else ""
        final_image_url = f"https://{bucket_name}.s3{region_part}.amazonaws.com/{s3_key}"
        print(f"✅ Edited image uploaded to S3: {final_image_url}")
        return final_image_url
    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Failed to upload edited image to S3: {str(e)}")
        raise
    except boto3.exceptions.S3TransferFailedError as e:
        print(f"❌ S3 transfer failed for edited image: {str(e)}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error during S3 upload: {str(e)}")
        raise


def edit_image_with_flux_from_url(prompt, image_url, keywords=None, output_dir="edited_images", strength=0.8):
    """Edit an image using FLUX AI via fal.ai API using image URL"""
    try:
        _configure_fal_client()
    except ValueError as e:
        return False, None, prompt, str(e)

    try:
        print(f"Starting FLUX AI image editing via fal.ai with URL...")

        enhanced_prompt = optimize_image_editing_prompt(prompt, keywords)
        print(f"Original prompt: {prompt}")
        print(f"Enhanced prompt: {enhanced_prompt}")

        strength = max(0.1, min(1.0, strength))

        result = fal_client.subscribe(
            "fal-ai/flux/dev/image-to-image",
            arguments={
                "prompt": enhanced_prompt,
                "image_url": image_url,
                "strength": strength,
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_images": 1,
                "enable_safety_checker": True,
            },
        )

        if not result or "images" not in result or not result["images"]:
            error_msg = "No edited image returned from fal.ai FLUX model"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg

        edited_image_url = result["images"][0]["url"]
        if not edited_image_url:
            error_msg = "No edited image URL returned from fal.ai"
            print(f"Error: {error_msg}")
            return False, None, enhanced_prompt, error_msg

        final_image_url = upload_image_from_url(edited_image_url, output_dir)
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
