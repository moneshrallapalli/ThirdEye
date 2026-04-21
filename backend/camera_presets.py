"""
Location-based default task presets for cameras.

When a camera is added with a recognized location keyword,
these tasks are automatically assigned to it.
"""

LOCATION_PRESETS = {
    "kitchen": [
        {
            "command": "Watch for fire, smoke, or any signs of burning on the stove or oven",
            "task_type": "fire_detection",
            "priority": 3,
        },
        {
            "command": "Alert if the stove or oven is left on with no one in the kitchen for more than 2 minutes",
            "task_type": "safety_monitoring",
            "priority": 2,
        },
    ],
    "garden": [
        {
            "command": "Watch for unauthorized people entering the property or trespassing",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
        {
            "command": "Alert if someone steps on the grass, flower beds, or damages plants",
            "task_type": "property_monitoring",
            "priority": 1,
        },
    ],
    "entrance": [
        {
            "command": "Watch for unknown or suspicious people approaching the door",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
        {
            "command": "Alert if a package or delivery is left at the door",
            "task_type": "package_detection",
            "priority": 1,
        },
    ],
    "front door": [
        {
            "command": "Watch for unknown or suspicious people approaching the door",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
        {
            "command": "Alert if a package or delivery is left at the door",
            "task_type": "package_detection",
            "priority": 1,
        },
    ],
    "back door": [
        {
            "command": "Watch for unauthorized people trying to enter through the back door",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
    ],
    "parking": [
        {
            "command": "Watch for unauthorized vehicles or unknown people near parked cars",
            "task_type": "vehicle_monitoring",
            "priority": 2,
        },
        {
            "command": "Alert if someone approaches or tampers with a parked vehicle",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
    ],
    "garage": [
        {
            "command": "Alert if the garage door is left open with no activity for an extended period",
            "task_type": "state_monitoring",
            "priority": 2,
        },
        {
            "command": "Watch for unauthorized entry into the garage",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
    ],
    "living room": [
        {
            "command": "Monitor for unusual activity or unknown people in the living room",
            "task_type": "activity_monitoring",
            "priority": 2,
        },
    ],
    "bedroom": [
        {
            "command": "Alert if unexpected motion or unknown people are detected in the bedroom",
            "task_type": "motion_detection",
            "priority": 2,
        },
    ],
    "office": [
        {
            "command": "Watch for unauthorized access or unknown people in the workspace",
            "task_type": "access_monitoring",
            "priority": 2,
        },
    ],
    "warehouse": [
        {
            "command": "Watch for unauthorized entry or suspicious behavior near stored goods",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
        {
            "command": "Alert if items are being moved or removed without authorization",
            "task_type": "theft_detection",
            "priority": 3,
        },
    ],
    "pool": [
        {
            "command": "Alert if a child or pet enters the pool area unsupervised",
            "task_type": "safety_monitoring",
            "priority": 3,
        },
    ],
    "baby room": [
        {
            "command": "Alert if the baby is crying, in distress, or attempting to climb out of the crib",
            "task_type": "safety_monitoring",
            "priority": 3,
        },
    ],
    "nursery": [
        {
            "command": "Alert if the baby is crying, in distress, or attempting to climb out of the crib",
            "task_type": "safety_monitoring",
            "priority": 3,
        },
    ],
    "driveway": [
        {
            "command": "Watch for vehicles or people arriving at or leaving the driveway",
            "task_type": "activity_monitoring",
            "priority": 2,
        },
        {
            "command": "Alert if an unknown person lingers in the driveway",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
    ],
    "backyard": [
        {
            "command": "Watch for unauthorized people entering the backyard",
            "task_type": "intrusion_detection",
            "priority": 3,
        },
    ],
    "shop": [
        {
            "command": "Watch for shoplifting or suspicious behavior around merchandise",
            "task_type": "theft_detection",
            "priority": 3,
        },
    ],
    "store": [
        {
            "command": "Watch for shoplifting or suspicious behavior around merchandise",
            "task_type": "theft_detection",
            "priority": 3,
        },
    ],
}


def get_preset_tasks(location: str) -> list:
    """
    Return preset tasks for a given location string.
    Matches against known location keywords (case-insensitive, partial match).
    """
    if not location:
        return []

    loc = location.strip().lower()

    # Exact match first
    if loc in LOCATION_PRESETS:
        return LOCATION_PRESETS[loc]

    # Partial / keyword match
    for key, tasks in LOCATION_PRESETS.items():
        if key in loc or loc in key:
            return tasks

    return []


def get_all_presets() -> dict:
    """Return all available location presets for the frontend."""
    result = {}
    for location, tasks in LOCATION_PRESETS.items():
        result[location] = [
            {"command": t["command"], "task_type": t["task_type"]}
            for t in tasks
        ]
    return result
