import argparse
from tools.ai.blog_generator.blog_writing.blog_writer import BlogWriter

def main():
    """Main function to run the blog writer system."""
    parser = argparse.ArgumentParser(description='Multi-Agent Blog Writer')
    parser.add_argument('--topic', type=str, required=True, help='Topic for the blog post')
    parser.add_argument('--output', type=str, help='Output file for the blog post')
    parser.add_argument('--custom-llm', action='store_true', help='Use custom Gemini LLM')
    parser.add_argument('--no-image', action='store_true', help='Skip banner image generation')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting Blog Writer Multi-Agent System")
    print(f"📝 Topic: {args.topic}")
    print(f"{'='*60}\n")
    
    print("1️⃣ Initializing agents...")
    blog_writer = BlogWriter(
        use_custom_llm=args.custom_llm,
        generate_banner_image=not args.no_image,
        topic=args.topic
    )
    
    print("\n2️⃣ Starting the writing process...\n")
    output_file, image_path = blog_writer.save_blog_to_file(args.topic, args.output)
    
    print(f"\n{'='*60}")
    print(f"✅ Blog post generation complete!")
    print(f"📄 Blog post saved to: {output_file}")
    
    if image_path:
        print(f"🖼️ Banner image saved to: {image_path}")
    
    print(f"{'='*60}\n")
    print(f"To view the blog post, you can open the file with any markdown viewer or text editor.")
    print(f"Thanks for using the Blog Writer Multi-Agent System!\n")

if __name__ == "__main__":
    main()
    
    