"""
Offline RL training script.
Trains a PPO agent on simulated episodes of the smart grid environment.

Usage:
    python -m ai.train --timesteps 100000
"""

import os
import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import EvalCallback, BaseCallback
    from stable_baselines3.common.monitor import Monitor
except ImportError:
    logger.error("stable-baselines3 is required for training.")
    logger.error("Install with: pip install stable-baselines3[extra]")
    sys.exit(1)

from simulation.grid_environment import SmartGridEnv


class TrainingLogCallback(BaseCallback):
    """Custom callback to log training progress."""

    def __init__(self, log_interval=5000, verbose=0):
        super().__init__(verbose)
        self.log_interval = log_interval

    def _on_step(self) -> bool:
        if self.n_calls % self.log_interval == 0:
            # Get recent episode info
            if len(self.model.ep_info_buffer) > 0:
                recent = list(self.model.ep_info_buffer)[-5:]
                avg_reward = sum(ep["r"] for ep in recent) / len(recent)
                avg_length = sum(ep["l"] for ep in recent) / len(recent)
                logger.info(
                    f"Step {self.n_calls:,} | "
                    f"Avg Reward: {avg_reward:.2f} | "
                    f"Avg Length: {avg_length:.0f}"
                )
        return True


def train(timesteps: int = 100_000, save_path: str = None):
    """Train the PPO agent."""
    if save_path is None:
        save_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "models", "ppo_smart_grid"
        )

    # Create model directory
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # Create training environment
    # Shorter episodes for faster training (1 simulated day = 43200 steps at 2s/step)
    # We use 4320 steps = ~2.4 hours per episode for faster iteration
    env = Monitor(SmartGridEnv(steps_per_episode=4320))

    # Create eval environment
    eval_env = Monitor(SmartGridEnv(steps_per_episode=4320))

    logger.info(f"Training PPO agent for {timesteps:,} timesteps...")
    logger.info(f"Model will be saved to: {save_path}")

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=0,
        tensorboard_log=os.path.join(os.path.dirname(save_path), "tb_logs"),
    )

    callbacks = [
        TrainingLogCallback(log_interval=5000),
        EvalCallback(
            eval_env,
            best_model_save_path=os.path.dirname(save_path),
            log_path=os.path.dirname(save_path),
            eval_freq=10000,
            n_eval_episodes=5,
            deterministic=True,
        ),
    ]

    model.learn(total_timesteps=timesteps, callback=callbacks)
    model.save(save_path)
    logger.info(f"Model saved to {save_path}.zip")

    # Quick evaluation
    logger.info("Running evaluation...")
    obs, _ = eval_env.reset()
    total_reward = 0
    steps = 0
    done = False

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = eval_env.step(action)
        total_reward += reward
        steps += 1
        done = terminated or truncated

    logger.info(f"Evaluation: {steps} steps, total reward: {total_reward:.2f}")
    logger.info(f"Final cost: ${info.get('total_cost', 0):.4f}")
    logger.info(f"Blackouts: {info.get('blackout_count', 0)}")

    env.close()
    eval_env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RL agent for smart grid")
    parser.add_argument("--timesteps", type=int, default=100_000,
                        help="Total training timesteps")
    parser.add_argument("--save-path", type=str, default=None,
                        help="Path to save trained model")
    args = parser.parse_args()
    train(args.timesteps, args.save_path)
