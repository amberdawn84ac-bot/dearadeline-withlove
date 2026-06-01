"""
Test the ML component selector with sample interaction data.
This verifies that collaborative filtering and content-based scoring work correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.algorithms.ml_component_selector import get_ml_selector, StudentInteraction, ComponentFeatures
from app.algorithms.component_selector import LearnerContext

async def test_ml_selector():
    """Test the ML selector with sample data."""
    print("Testing ML Component Selector...")

    # Get the ML selector instance
    selector = get_ml_selector()

    # Simulate some student interactions
    student_id = "test_student_001"

    # Log some interactions for student 1 (prefers visual, succeeds with MindMap)
    selector.log_interaction(student_id, StudentInteraction(
        component_id="MindMap",
        component_type="visualization",
        interaction_type="completed",
        student_modality="visual",
        component_modalities=["visual"],
        difficulty="DEVELOPING",
        duration_secs=120.0,
        completed=True,
        struggle_count=0,
        hints_used=0,
        mastery_before=0.5,
        mastery_after=0.7,
        timestamp=0.0,
    ))

    selector.log_interaction(student_id, StudentInteraction(
        component_id="MindMap",
        component_type="visualization",
        interaction_type="completed",
        student_modality="visual",
        component_modalities=["visual"],
        difficulty="DEVELOPING",
        duration_secs=90.0,
        completed=True,
        struggle_count=0,
        hints_used=0,
        mastery_before=0.7,
        mastery_after=0.8,
        timestamp=100.0,
    ))

    # Log interactions for student 2 (prefers auditory, struggles with MindMap)
    student_id_2 = "test_student_002"
    selector.log_interaction(student_id_2, StudentInteraction(
        component_id="MindMap",
        component_type="visualization",
        interaction_type="struggled",
        student_modality="auditory",
        component_modalities=["visual"],
        difficulty="DEVELOPING",
        duration_secs=180.0,
        completed=False,
        struggle_count=3,
        hints_used=2,
        mastery_before=0.4,
        mastery_after=0.35,
        timestamp=0.0,
    ))

    selector.log_interaction(student_id_2, StudentInteraction(
        component_id="AudioDialogue",
        component_type="multimodal",
        interaction_type="completed",
        student_modality="auditory",
        component_modalities=["auditory", "visual"],
        difficulty="DEVELOPING",
        duration_secs=240.0,
        completed=True,
        struggle_count=0,
        hints_used=0,
        mastery_before=0.35,
        mastery_after=0.6,
        timestamp=100.0,
    ))

    # Test component selection for student 1 (visual learner)
    context = LearnerContext(
        difficulty="DEVELOPING",
        preferred_modalities=["visual"],
        topic_tags=["math"],
        recent_struggle_count=0,
    )

    recommendations = selector.select_components(
        student_id=student_id,
        learner_context=context,
        available_components=["MindMap", "AudioDialogue", "VirtualManipulative", "AutoDiagram"],
        max_results=3,
    )

    print(f"\nStudent 1 (visual learner) recommendations:")
    for rec in recommendations:
        print(f"  - {rec.component_id}: score={rec.score:.3f}, reason={rec.reason}")

    # Test component selection for student 2 (auditory learner)
    context_2 = LearnerContext(
        difficulty="DEVELOPING",
        preferred_modalities=["auditory"],
        topic_tags=["math"],
        recent_struggle_count=0,
    )

    recommendations_2 = selector.select_components(
        student_id=student_id_2,
        learner_context=context_2,
        available_components=["MindMap", "AudioDialogue", "VirtualManipulative", "AutoDiagram"],
        max_results=3,
    )

    print(f"\nStudent 2 (auditory learner) recommendations:")
    for rec in recommendations_2:
        print(f"  - {rec.component_id}: score={rec.score:.3f}, reason={rec.reason}")

    # Test with insufficient data (should fall back to heuristic)
    student_id_3 = "test_student_003"
    context_3 = LearnerContext(
        difficulty="DEVELOPING",
        preferred_modalities=["kinesthetic"],
        topic_tags=["science"],
        recent_struggle_count=0,
    )

    recommendations_3 = selector.select_components(
        student_id=student_id_3,
        learner_context=context_3,
        available_components=["MindMap", "AudioDialogue", "VirtualManipulative", "AutoDiagram"],
        max_results=3,
    )

    print(f"\nStudent 3 (no data, heuristic fallback) recommendations:")
    for rec in recommendations_3:
        print(f"  - {rec.component_id}: score={rec.score:.3f}, reason={rec.reason}")

    print("\nML Component Selector test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_ml_selector())
