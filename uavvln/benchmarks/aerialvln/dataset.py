"""AerialVLN episode adapter for JSON/JSONL records."""
import json
from pathlib import Path
from uavvln.core.episode import EpisodeSpec, PointGoal
from uavvln.core.pose import Pose

def episode_from_record(record):
    start = record.get("start_pose", {})
    position = start.get("position", record.get("start_position", [0, 0, 0]))
    quaternion = start.get("quaternion", [0, 0, 0, 1])
    goal = record.get("goal", record.get("goal_position", [0, 0, 0]))
    if isinstance(goal, dict): goal = goal.get("position", [0, 0, 0])
    metadata = dict(record.get("metadata", {}))
    if "split" in record: metadata.setdefault("split", record["split"])
    return EpisodeSpec(str(record.get("episode_id", record.get("id", "unknown"))),
        str(record.get("scene_id", record.get("scene", "unknown"))),
        str(record.get("instruction", "")), Pose(position, quaternion),
        PointGoal(goal, float(record.get("success_radius", 1.0))),
        metadata=metadata)

def load_episodes(path, split=None):
    path = Path(path); text = path.read_text(encoding="utf-8")
    records = json.loads(text) if path.suffix.lower() == ".json" else [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(records, dict): records = records.get("episodes", records.get("data", []))
    if split is not None: records = [r for r in records if r.get("split", split) == split]
    return [episode_from_record(record) for record in records]
