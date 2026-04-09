import asyncio
from app.services.sefaria import fetch_biblical_text

async def test():
    print("Testing Genesis 1:1 fetch with Everett Fox version...")
    result = await fetch_biblical_text("Genesis.1.1")
    
    if result:
        print(f"\n✅ Fetch successful!")
        print(f"Ref: {result['ref']}")
        print(f"Version Title: {result['version_title']}")
        print(f"Is Fox: {result['is_fox']}")
        print(f"\nEnglish text:")
        print(result['english'][:200])
        print(f"\nHebrew text:")
        print(result['hebrew'][:100])
    else:
        print("❌ Fetch failed")

if __name__ == "__main__":
    asyncio.run(test())
