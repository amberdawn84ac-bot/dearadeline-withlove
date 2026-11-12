"""Reviewed teaching material for the saved horse anatomy scene."""

PLATE_PATH = "/lesson-media/horse-superficial-muscles.jpg"

PLATE_SOURCE = {
    "id": "stillman-horse-in-motion-plate-iii",
    "kind": "link",
    "title": "The Horse in Motion, Plate III",
    "url": "https://upload.wikimedia.org/wikipedia/commons/3/34/The_horse_in_motion_-_as_shown_by_instantaneous_photography_-_with_a_study_on_animal_mechanics_founded_on_anatomy_and_the_revelations_of_the_camera_-_in_which_is_demonstrated_the_theory_of_%28IA_horseinmotionass01stil%29.pdf#page=43",
    "attribution": "J. D. B. Stillman, The Horse in Motion (1882). Boston Public Library scan. Public domain. Illustration cropped.",
}


def restore_equine_anatomy(scene: dict, teacher_id: str) -> dict:
    if (
        scene["type"] != "slide"
        or scene["title"].strip().casefold() != "mapping the horse: anatomy for touch"
    ):
        return scene
    return {
        **scene,
        "content": (
            "Watch a horse take one slow step in a video or from outside the fence. "
            "Follow the top of the shoulder as the near front hoof lifts and reaches forward. "
            "The scapula, or shoulder blade, lies against the side of the rib cage. "
            "Muscles suspend and move it. That freedom lets the shoulder blade contribute to the stride."
        ),
        "visual": {
            "reading": (
                "Start at the withers, the rise where the base of the neck meets the back. "
                "In this side view the horse faces right. The pale strip sloping down and forward "
                "below the withers helps you orient yourself to the shoulder blade."
            ),
            "elements": [
                {
                    "id": "equine-muscle-plate",
                    "type": "image",
                    "url": PLATE_PATH,
                    "alt": "Side view of a horse facing right, with exposed muscle groups along its neck, shoulder, back and hindquarters.",
                    "text": "Plate III. Use g for the trapezius near the withers and d for the broad muscle behind the shoulder.",
                },
                {
                    "id": "equine-muscle-key",
                    "type": "table",
                    "text": "From a landmark to a movement",
                    "headers": ["Find it", "What it helps explain"],
                    "rows": [
                        ["Withers and trapezius (g)", "The withers are a bony landmark. The trapezius attaches to the ridge on the shoulder blade and helps position the blade as the forelimb moves."],
                        ["Latissimus dorsi (d)", "This broad muscle runs from the back toward the upper forelimb. Its pull helps bring the forelimb backward relative to the trunk."],
                        ["Hip and front of the thigh", "The quadriceps group lies along the front of the thigh. It straightens the stifle, the hindlimb joint comparable to our knee. Much of the group sits deeper than the surface shown here."],
                    ],
                },
            ],
        },
        "worked_example": (
            "Pause a side-view video once with the near front hoof reaching forward and again "
            "after the hoof is planted and the body has moved ahead. Compare the upper forelimb "
            "with a vertical line under the withers. The angle changes relative to the body even "
            "while the hoof is planted. That is evidence of movement at the upper limb. "
            "It takes more than a video frame to identify which muscle is active."
        ),
        "actions": [
            {"role_id": teacher_id, "kind": "focus", "target_id": "equine-muscle-plate", "text": "Find the withers at the base of the neck. Trace down and forward toward the shoulder. Now try following that same line in a walking video."},
            {"role_id": teacher_id, "kind": "annotate", "target_id": "equine-muscle-plate", "note": "Follow the d labels from the back toward the upper forelimb.", "text": "Picture a pull directed back toward the trunk. Which way would that pull tend to move the upper forelimb?"},
            {"role_id": teacher_id, "kind": "focus", "target_id": "equine-muscle-key", "text": "Compare the shoulder blade with the stifle. One glides against the rib cage. The other bends and straightens as the hind limb takes a step."},
        ],
        "key_points": [],
        "resources": [PLATE_SOURCE, *(scene.get("resources") or [])],
    }
