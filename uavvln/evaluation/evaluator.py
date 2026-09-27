from dataclasses import dataclass

@dataclass(frozen=True)
class EpisodeResult:
    episode_id: str
    success: bool
    steps: int
    final_distance: float
    collisions: int

def evaluate_episode(environment, agent, episode):
    observation = environment.reset(episode); agent.reset(episode)
    result = None
    while True:
        result = environment.step(agent.act(observation))
        observation = result.observation
        if result.terminated or result.truncated: break
    return EpisodeResult(episode.episode_id, bool(result.info["success"]),
                         environment.steps, result.info["distance_to_goal"],
                         int(result.info["collision"]))

def evaluate(benchmark, environment, agent, split="test"):
    return [evaluate_episode(environment, agent, episode) for episode in benchmark.episodes(split)]
