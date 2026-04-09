"""
seed_all.py — Master Seed Script for Production Deployment

Runs all seed scripts in the correct order to populate Hippocampus
with a rich, balanced starting corpus across all tracks.

Usage:
    python scripts/seed_all.py
    python scripts/seed_all.py --skip-existing
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_all")


async def run_seed_script(script_name: str, description: str):
    """Run a seed script and report results."""
    log.info(f"\n{'='*70}")
    log.info(f"RUNNING: {description}")
    log.info(f"{'='*70}")
    
    try:
        # Import and run the script's main function
        if script_name == "seed_curriculum":
            from seed_curriculum import main as seed_main
        elif script_name == "seed_key_passages":
            from seed_key_passages import main as seed_main
        elif script_name == "seed_founding_documents":
            from seed_founding_documents import main as seed_main
        elif script_name == "seed_history_primary_sources":
            from seed_history_primary_sources import main as seed_main
        elif script_name == "seed_creation_science":
            from seed_creation_science import main as seed_main
        else:
            log.error(f"Unknown script: {script_name}")
            return False
        
        await seed_main()
        log.info(f"✓ Completed: {description}")
        return True
        
    except Exception as e:
        log.error(f"✗ Failed: {description} - {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Run all seed scripts for production deployment")
    parser.add_argument("--skip-existing", action="store_true", help="Skip documents that already exist")
    args = parser.parse_args()
    
    log.info(f"\n{'#'*70}")
    log.info(f"# ADELINE PRODUCTION SEEDING")
    log.info(f"# Populating Hippocampus with foundational curriculum")
    log.info(f"{'#'*70}\n")
    
    # Track results
    results = {}
    
    # Seed in priority order
    seed_order = [
        ("seed_key_passages", "Key Bible Passages (Discipleship Track)"),
        ("seed_founding_documents", "U.S. Founding Documents (Declaration, Constitution, Bill of Rights)"),
        ("seed_history_primary_sources", "Historical Primary Sources (20+ documents across all eras)"),
        ("seed_curriculum", "Frederick Douglass & OAS Standards"),
        ("seed_creation_science", "Creation Science Experiments"),
    ]
    
    for script_name, description in seed_order:
        success = await run_seed_script(script_name, description)
        results[description] = success
        
        # Brief pause between scripts
        await asyncio.sleep(1)
    
    # Final summary
    log.info(f"\n{'#'*70}")
    log.info(f"# SEEDING COMPLETE")
    log.info(f"{'#'*70}\n")
    
    log.info("Results:")
    for description, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        log.info(f"  {status}: {description}")
    
    total_success = sum(1 for s in results.values() if s)
    total_scripts = len(results)
    
    log.info(f"\nOverall: {total_success}/{total_scripts} scripts completed successfully")
    
    if total_success == total_scripts:
        log.info("\n🎉 Hippocampus is ready for production!")
        log.info("Next steps:")
        log.info("  1. Add TAVILY_API_KEY to Railway environment variables")
        log.info("  2. Deploy to Railway")
        log.info("  3. Test with sample queries:")
        log.info("     - 'Tell me about Isaiah 43:1' (Sefaria integration)")
        log.info("     - 'What is the Declaration of Independence?' (Seeded history)")
        log.info("     - 'Show me a seed germination experiment' (Creation Science)")
        log.info("     - 'Tell me about the Civil War' (Web search + auto-seed)")
    else:
        log.warning("\n⚠️  Some scripts failed. Review errors above.")


if __name__ == "__main__":
    asyncio.run(main())
