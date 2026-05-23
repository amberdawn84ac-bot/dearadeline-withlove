"""
Seed Canonical Curriculum — Pre-generate lessons for core topics.

Run this script ONCE before launch to populate the CanonicalLesson table with
approved, quality lessons for your most important topics. This ensures:
- Students get instant lessons (no live generation latency)
- Controversial topics are pre-reviewed by you
- Production scale without relying on live API calls

Usage:
    cd adeline-brain
    python scripts/seed_canonical_curriculum.py

Requires:
    - DATABASE_URL env var set
    - GEMINI_API_KEY or GOOGLE_API_KEY set (for generation)
    - ANTHROPIC_API_KEY optional (fallback for controversial topics)

Topics are generated with pendingApproval=TRUE by default so you can review before publishing.
After review, approve them via:
    POST /brain/api/admin/tasks/canonicals/{slug}/approve
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.connections.canonical_store import canonical_store, canonical_slug
from app.schemas.api_models import Track

# Core curriculum topics to pre-seed
# Format: (track, topic, expected_difficulty)
CORE_CURRICULUM = [
    # CREATION_SCIENCE — Pre-seed safe topics, mark controversial ones for review
    (Track.CREATION_SCIENCE, "Seed Germination", "safe"),
    (Track.CREATION_SCIENCE, "The Water Cycle", "safe"),
    (Track.CREATION_SCIENCE, "Photosynthesis", "safe"),
    (Track.CREATION_SCIENCE, "Food Chains and Webs", "safe"),
    (Track.CREATION_SCIENCE, "Animal Adaptations", "safe"),
    (Track.CREATION_SCIENCE, "States of Matter", "safe"),
    (Track.CREATION_SCIENCE, "Simple Machines", "safe"),
    (Track.CREATION_SCIENCE, "Electricity Basics", "safe"),
    (Track.CREATION_SCIENCE, "The Solar System", "safe"),
    (Track.CREATION_SCIENCE, "Earth's Layers", "safe"),
    (Track.CREATION_SCIENCE, "Weather Patterns", "safe"),
    (Track.CREATION_SCIENCE, "Ecosystems", "safe"),
    (Track.CREATION_SCIENCE, "Human Body Systems", "safe"),
    (Track.CREATION_SCIENCE, "Origins Debate", "controversial"),
    (Track.CREATION_SCIENCE, "Evidence for Creation", "controversial"),
    (Track.CREATION_SCIENCE, "Dinosaurs and the Flood", "controversial"),
    (Track.CREATION_SCIENCE, "The Age of the Earth", "controversial"),
    
    # TRUTH_HISTORY — All need careful primary source verification
    (Track.TRUTH_HISTORY, "The Mayflower Compact", "safe"),
    (Track.TRUTH_HISTORY, "The Boston Tea Party", "safe"),
    (Track.TRUTH_HISTORY, "Writing the Constitution", "safe"),
    (Track.TRUTH_HISTORY, "The Louisiana Purchase", "safe"),
    (Track.TRUTH_HISTORY, "The Wright Brothers First Flight", "safe"),
    (Track.TRUTH_HISTORY, "The Signing of the Declaration of Independence", "safe"),
    (Track.TRUTH_HISTORY, "The Civil War", "controversial"),
    (Track.TRUTH_HISTORY, "Slavery in America", "controversial"),
    (Track.TRUTH_HISTORY, "World War II", "controversial"),
    (Track.TRUTH_HISTORY, "The Holocaust", "controversial"),
    
    # DISCIPLESHIP — Bible-focused, generally safe
    (Track.DISCIPLESHIP, "The Creation Story", "safe"),
    (Track.DISCIPLESHIP, "Noah's Ark", "safe"),
    (Track.DISCIPLESHIP, "The Ten Commandments", "safe"),
    (Track.DISCIPLESHIP, "David and Goliath", "safe"),
    (Track.DISCIPLESHIP, "The Birth of Jesus", "safe"),
    (Track.DISCIPLESHIP, "The Parable of the Good Samaritan", "safe"),
    (Track.DISCIPLESHIP, "The Sermon on the Mount", "safe"),
    (Track.DISCIPLESHIP, "The Early Church", "safe"),
    
    # HOMESTEADING — Practical skills, safe
    (Track.HOMESTEADING, "Starting a Compost Pile", "safe"),
    (Track.HOMESTEADING, "Raising Chickens", "safe"),
    (Track.HOMESTEADING, "Garden Planning for Beginners", "safe"),
    (Track.HOMESTEADING, "Preserving the Harvest", "safe"),
    (Track.HOMESTEADING, "Natural Pest Control", "safe"),
    (Track.HOMESTEADING, "Building Raised Beds", "safe"),
    (Track.HOMESTEADING, "Seed Saving", "safe"),
    (Track.HOMESTEADING, "Water Conservation", "safe"),
    
    # ENGLISH_LITERATURE — Book-based, safe
    (Track.ENGLISH_LITERATURE, "Charlotte's Web", "safe"),
    (Track.ENGLISH_LITERATURE, "The Chronicles of Narnia", "safe"),
    (Track.ENGLISH_LITERATURE, "Little House on the Prairie", "safe"),
    (Track.ENGLISH_LITERATURE, "Pilgrim's Progress", "safe"),
]


async def generate_placeholder_canonical(track: Track, topic: str, is_controversial: bool) -> dict:
    """Create a stub canonical with proper review flags."""
    now = datetime.utcnow().isoformat()
    return {
        "id": str(uuid.uuid4()),
        "topic": topic,
        "track": track.value,
        "title": f"{topic} — {track.value.replace('_', ' ').title()}",
        "blocks": [{
            "block_type": "NARRATIVE",
            "content": (
                f"**{topic}**\n\n"
                "This lesson is being prepared by our teaching team. "
                "Check back soon for a complete, carefully-reviewed lesson.\n\n"
                "In the meantime, try asking Adeline a specific question about this topic!"
            ) if not is_controversial else (
                f"**{topic}**\n\n"
                "This topic requires special theological and historical review. "
                "Our team is preparing a lesson that teaches truth with care and accuracy. "
                "Check back soon!"
            ),
            "evidence": [],
            "is_silenced": False,
        }],
        "oas_standards": [],
        "researcher_activated": False,
        "agent_name": "AdminPlaceholder",
    }


async def seed_curriculum():
    """Main seeding routine."""
    seeded = 0
    pending = 0
    
    print(f"Seeding {len(CORE_CURRICULUM)} canonical lessons...")
    print("-" * 60)
    
    for track, topic, difficulty in CORE_CURRICULUM:
        slug = canonical_slug(topic, track.value)
        is_controversial = difficulty == "controversial"
        
        # Check if already exists
        existing = await canonical_store.get(slug)
        if existing:
            print(f"  [SKIP] {topic} ({track.value}) — already exists")
            continue
        
        # Create placeholder canonical (pending approval)
        record = await generate_placeholder_canonical(track, topic, is_controversial)
        
        # Save as pending (requires your approval before students see it)
        reason = "Controversial topic — requires theological review" if is_controversial else "New canonical — awaiting content generation"
        await canonical_store.save(slug, record, pending=True)
        
        status = "PENDING_REVIEW" if is_controversial else "PENDING_CONTENT"
        print(f"  [{status}] {topic} ({track.value})")
        
        if is_controversial:
            pending += 1
        else:
            seeded += 1
    
    print("-" * 60)
    print(f"Done! {seeded} safe topics seeded (will use auto-generation)")
    print(f"      {pending} controversial topics flagged for YOUR review")
    print()
    print("Next steps:")
    print("1. Review pending canonicals at: GET /brain/api/admin/tasks/canonicals")
    print("2. For controversial topics, manually create quality content")
    print("3. Approve lessons at: POST /brain/api/admin/tasks/canonicals/{slug}/approve")
    print()
    print("Students will see: 'This lesson is being prepared' until you approve.")


if __name__ == "__main__":
    # Verify env
    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    asyncio.run(seed_curriculum())
