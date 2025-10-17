import os
import requests
import boto3
import io
import time
from datetime import datetime
from openai import OpenAI
import fal_client
from django.conf import settings  # ✅ using Django settings
from .prompts import FLUX_AI_OPTIMIZATION_PROMPT


# Configure fal_client with API key
def _configure_fal_client():
    """Configure fal_client with API key from Django settings"""
    api_key = getattr(settings, "FAL_KEY", None)
    if not api_key:
        raise ValueError("FAL_KEY not found in Django settings")
    fal_client.api_key = api_key


def optimize_image_prompt_for_flux(prompt, topic=None, keywords=None, image_type="content", image_number=1):
    """Optimize the image generation prompt specifically for FLUX AI"""
    try:
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            return prompt  # fallback if missing

        client = OpenAI(api_key=api_key)

        topic_context = f" about {topic}" if topic else ""
        keywords_context = f" focusing on these keywords: {', '.join(keywords)}" if keywords else ""
        system_message = FLUX_AI_OPTIMIZATION_PROMPT

        variation_instruction = ""
        if image_number > 1:
            variation_instruction = (
                f" This is image #{image_number} in a series, so create a unique artistic style "
                "or perspective while maintaining thematic consistency."
            )

        user_message = (
            f"Optimize this prompt for FLUX AI image generation{topic_context}{keywords_context}: "
            f"{prompt}{variation_instruction}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=400,
        )

        optimized_prompt = response.choices[0].message.content.strip()
        if not optimized_prompt or len(optimized_prompt) < 20:
            return prompt

        return optimized_prompt

    except Exception as e:
        print(f"Error optimizing image prompt for FLUX AI: {str(e)}")
        return prompt


def upload_image_to_s3(image_content, output_dir, filename):
    """Upload image to S3 with improved error handling"""
    s3_key = f"{output_dir}/{filename}"

    # ✅ Get S3 credentials directly from Django settings
    aws_access_key = settings.AWS_ACCESS_KEY_ID
    aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
    bucket_name = settings.S3_BUCKET_NAME
    region = settings.AWS_REGION

    # Debug logging
    print(f"🔍 S3 Debug Info:")
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

    # Upload image to S3 directly with improved error handling
    try:
        s3_client.upload_fileobj(
            io.BytesIO(image_content),
            bucket_name,
            s3_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
        region_part = f".{region}" if region and region != "us-east-1" else ""
        final_image_url = f"https://{bucket_name}.s3{region_part}.amazonaws.com/{s3_key}"
        print(f"✅ Image uploaded to S3: {final_image_url}")
        return final_image_url
    except boto3.exceptions.S3UploadFailedError as e:
        print(f"❌ Failed to upload image to S3: {str(e)}")
        raise
    except boto3.exceptions.S3TransferFailedError as e:
        print(f"❌ S3 transfer failed: {str(e)}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error during S3 upload: {str(e)}")
        raise


def generate_image_with_flux(prompt, size="1920x1080", output_dir="blog_images",
                             topic=None, keywords=None, image_type="content", count=1):
    """Generate one or more images using FLUX AI via fal.ai API and upload to S3"""
    if not prompt or not prompt.strip():
        fallback_topic = topic if topic else "Professional content"
        keyword_focus = f" featuring {', '.join(keywords[:3])}" if keywords else ""
        prompt = (
            f"Create a professional, high-quality image about {fallback_topic}{keyword_focus} "
            "with intricate details and artistic composition."
        )
        topic = fallback_topic

    count = max(1, min(count, 10))

    try:
        _configure_fal_client()
    except ValueError as e:
        print(f"Error: {str(e)}")
        return [], 0, count

    images_data = []
    failed_generations = 0

    image_size_map = {
        "1024x1024": "square_hd",
        "1024x1792": "portrait_16_9",
        "1792x1024": "landscape_16_9",
        "1920x1080": "landscape_16_9",
        "512x512": "square",
        "768x1024": "portrait_4_3",
        "1024x768": "landscape_4_3",
    }

    image_size = image_size_map.get(size, "square_hd")

    for i in range(count):
        try:
            image_number = i + 1
            print(f"Generating FLUX AI image {image_number} of {count}...")

            optimized_prompt = optimize_image_prompt_for_flux(prompt, topic, keywords, image_type, image_number)
            print(f"Image {image_number} - Optimized prompt: {optimized_prompt}")

            result = fal_client.subscribe(
                "fal-ai/flux/dev",
                arguments={
                    "prompt": optimized_prompt,
                    "image_size": image_size,
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "num_images": 1,
                    "enable_safety_checker": True,
                },
            )

            if not result or "images" not in result or not result["images"]:
                print(f"Error: No image returned from fal.ai for image {image_number}")
                failed_generations += 1
                continue

            image_url = result["images"][0]["url"]
            if not image_url:
                failed_generations += 1
                continue

            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                failed_generations += 1
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flux_ai_{timestamp}_img{image_number}.jpg"
            final_image_url = upload_image_to_s3(image_response.content, output_dir, filename)

            if not final_image_url:
                failed_generations += 1
                continue

            images_data.append({
                "image_url": final_image_url,
                "enhanced_prompt": optimized_prompt,
                "image_number": image_number,
                "generation_type": "flux_ai",
            })

            print(f"Successfully generated FLUX AI image {image_number}")

        except Exception as e:
            print(f"Error generating FLUX AI image {image_number}: {str(e)}")
            failed_generations += 1
            continue

    total_generated = len(images_data)
    print(f"FLUX AI generation complete: {total_generated} successful, {failed_generations} failed")
    return images_data, total_generated, failed_generations


def generate_image_with_flux_schnell(prompt, size="1920x1080", output_dir="blog_images",
                                     topic=None, keywords=None, image_type="content", count=1):
    """Generate images using FLUX Schnell (faster model) via fal.ai API and upload to S3"""
    if not prompt or not prompt.strip():
        fallback_topic = topic if topic else "Professional content"
        keyword_focus = f" featuring {', '.join(keywords[:3])}" if keywords else ""
        prompt = (
            f"Create a professional, high-quality image about {fallback_topic}{keyword_focus} "
            "with intricate details and artistic composition."
        )
        topic = fallback_topic

    count = max(1, min(count, 10))

    try:
        _configure_fal_client()
    except ValueError as e:
        print(f"Error: {str(e)}")
        return [], 0, count

    images_data = []
    failed_generations = 0

    image_size_map = {
        "1024x1024": "square_hd",
        "1024x1792": "portrait_16_9",
        "1792x1024": "landscape_16_9",
        "1920x1080": "landscape_16_9",
        "512x512": "square",
        "768x1024": "portrait_4_3",
        "1024x768": "landscape_4_3",
    }

    image_size = image_size_map.get(size, "square_hd")

    for i in range(count):
        try:
            image_number = i + 1
            print(f"Generating FLUX Schnell image {image_number} of {count}...")

            optimized_prompt = optimize_image_prompt_for_flux(prompt, topic, keywords, image_type, image_number)
            print(f"Image {image_number} - Optimized prompt: {optimized_prompt}")

            result = fal_client.subscribe(
                "fal-ai/flux/schnell",
                arguments={
                    "prompt": optimized_prompt,
                    "image_size": image_size,
                    "num_inference_steps": 4,
                    "num_images": 1,
                    "enable_safety_checker": True,
                },
            )

            if not result or "images" not in result or not result["images"]:
                failed_generations += 1
                continue

            image_url = result["images"][0]["url"]
            if not image_url:
                failed_generations += 1
                continue

            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                failed_generations += 1
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flux_schnell_{timestamp}_img{image_number}.jpg"
            final_image_url = upload_image_to_s3(image_response.content, output_dir, filename)

            if not final_image_url:
                failed_generations += 1
                continue

            images_data.append({
                "image_url": final_image_url,
                "enhanced_prompt": optimized_prompt,
                "image_number": image_number,
                "generation_type": "flux_schnell",
            })

            print(f"Successfully generated FLUX Schnell image {image_number}")

        except Exception as e:
            print(f"Error generating FLUX Schnell image {image_number}: {str(e)}")
            failed_generations += 1
            continue

    total_generated = len(images_data)
    print(f"FLUX Schnell generation complete: {total_generated} successful, {failed_generations} failed")
    return images_data, total_generated, failed_generations


def generate_image(prompt, size="1920x1080", output_dir="blog_images",
                   topic=None, image_type="content", count=1,
                   keywords=None, generation_method="flux"):
    """Main backward-compatible wrapper"""
    if generation_method not in ["flux", "flux_schnell"]:
        print(f"Warning: Invalid generation method '{generation_method}'. Defaulting to 'flux'.")
        generation_method = "flux"

    if generation_method == "flux_schnell":
        return generate_image_with_flux_schnell(prompt, size, output_dir, topic, keywords, image_type, count)
    else:
        return generate_image_with_flux(prompt, size, output_dir, topic, keywords, image_type, count)
