import asyncio
from app.services.sefaria import fetch_biblical_text, detect_biblical_reference

async def test():
    # Test detection
    ref = detect_biblical_reference("Genesis 1:1")
    print(f"Detected reference: {ref}")
    
    # Test fetch
    result = await fetch_biblical_text("Genesis.1.1")
    if result:
        print(f"✅ Fetch successful!")
        print(f"Ref: {result['ref']}")
        print(f"Is Fox: {result['is_fox']}")
        print(f"English: {result['english'][:100]}...")
        print(f"Hebrew: {result['hebrew'][:50]}...")
    else:
        print("❌ Fetch failed - returned None")

if __name__ == "__main__":
    asyncio.run(test())
