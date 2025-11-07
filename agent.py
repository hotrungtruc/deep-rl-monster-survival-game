from model import ZombieNet, hard_update, soft_update
from buffer import ReplayBuffer
import torch
import torch.optim as optim
import torch.nn.functional as F
import datetime
import time
import wandb  # Added import for wandb
import random
import os
from game import ZombieShooter
from pympler import asizeof
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import numpy as np
import csv
from collections import deque

class Agent():

    def __init__(self, env : ZombieShooter, dropout, hidden_layer, learning_rate, step_repeat, gamma):

        self.env = env

        self.step_repeat = step_repeat

        self.gamma = gamma

        observation, info = self.env.reset()

        self.device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

        print("Model loaded on: ", self.device)

        self.memory = ReplayBuffer(max_size=500000, input_shape=observation.shape, n_actions=env.action_space.n, device=self.device)

        self.model_1 = ZombieNet(action_dim=env.action_space.n, hidden_dim=hidden_layer, dropout=dropout, observation_shape=observation.shape).to(self.device)
        self.model_2 = ZombieNet(action_dim=env.action_space.n, hidden_dim=hidden_layer, dropout=dropout, observation_shape=observation.shape).to(self.device)  
        
        self.target_model_1 = ZombieNet(action_dim=env.action_space.n, hidden_dim=hidden_layer, dropout=dropout, observation_shape=observation.shape).to(self.device)  
        self.target_model_2 = ZombieNet(action_dim=env.action_space.n, hidden_dim=hidden_layer, dropout=dropout, observation_shape=observation.shape).to(self.device)  

        hard_update(self.target_model_1, self.model_1)
        hard_update(self.target_model_2, self.model_2)

        self.optimizer_1 = optim.Adam(self.model_1.parameters(), lr=learning_rate)
        self.optimizer_2 = optim.Adam(self.model_2.parameters(), lr=learning_rate)

        self.learning_rate = learning_rate

        # Store hyperparameters for logging
        self.dropout = dropout
        self.hidden_layer = hidden_layer

        print(f"Memory Size: {asizeof.asizeof(self.memory) / (1024 * 1024 * 1024):2f} Gb")

    
    def train(self, episodes, max_episode_steps, summary_writer_suffix,
          batch_size, epsilon, epsilon_decay, min_epsilon):

        # Login to wandb with the provided API key
        wandb.login(key="af6d254587eda268053f10932986d263cd1ea176")

        # Initialize wandb run
        wandb.init(
            project="ZombieShooter_Training",  # You can change the project name if needed
            name=summary_writer_suffix,
            config={
                "episodes": episodes,
                "max_episode_steps": max_episode_steps,
                "batch_size": batch_size,
                "epsilon": epsilon,
                "epsilon_decay": epsilon_decay,
                "min_epsilon": min_epsilon,
                "gamma": self.gamma,
                "learning_rate": self.learning_rate,
                "step_repeat": self.step_repeat,
                "dropout": self.dropout,
                "hidden_layer": self.hidden_layer,
            }
        )

        # === Tạo thư mục kết quả ===
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        result_dir = f"results/{timestamp}_{summary_writer_suffix}"
        os.makedirs(result_dir, exist_ok=True)

        total_steps = 0
        scores = []
        best_score = -float("inf")
        best_model_path = None
        recent_scores = deque(maxlen=10)  # để tính moving average

        # === Tạo file CSV log ===
        csv_path = os.path.join(result_dir, "training_log.csv")
        with open(csv_path, "w", newline="") as f:
            writer_csv = csv.writer(f)
            writer_csv.writerow(["Episode", "Score", "Epsilon", "Steps", "Time"])

        for episode in range(episodes):
            done = False
            episode_reward = 0
            state, info = self.env.reset()
            episode_steps = 0
            episode_start_time = time.time()

            while not done and episode_steps < max_episode_steps:
                # Epsilon-greedy policy
                if random.random() < epsilon:
                    action = self.env.action_space.sample()
                else:
                    q_values_1 = self.model_1.forward(state.unsqueeze(0).to(self.device))[0]
                    q_values_2 = self.model_2.forward(state.unsqueeze(0).to(self.device))[0]
                    q_values = torch.min(q_values_1, q_values_2)
                    action = torch.argmax(q_values, dim=-1).item()

                next_state, reward, done, _, _ = self.env.step(action=action, repeat=self.step_repeat)
                self.memory.store_transition(state, action, reward, next_state, done)
                state = next_state
                episode_reward += reward
                episode_steps += 1
                total_steps += 1

                # === Huấn luyện model ===
                if self.memory.can_sample(batch_size):
                    states, actions, rewards, next_states, dones = self.memory.sample_buffer(batch_size)
                    dones = dones.unsqueeze(1).float()

                    q_values_1 = self.model_1(states)
                    q_values_2 = self.model_2(states)
                    actions = actions.unsqueeze(1).long()
                    qsa_b_1 = q_values_1.gather(1, actions)
                    qsa_b_2 = q_values_2.gather(1, actions)

                    next_actions_1 = torch.argmax(self.model_1(next_states), dim=1, keepdim=True)
                    next_actions_2 = torch.argmax(self.model_2(next_states), dim=1, keepdim=True)
                    next_q_values_1 = self.target_model_1(next_states).gather(1, next_actions_1)
                    next_q_values_2 = self.target_model_2(next_states).gather(1, next_actions_2)
                    next_q_values = torch.min(next_q_values_1, next_q_values_2)

                    target_b = rewards.unsqueeze(1) + (1 - dones) * self.gamma * next_q_values

                    loss_1 = F.smooth_l1_loss(qsa_b_1, target_b.detach())
                    loss_2 = F.smooth_l1_loss(qsa_b_2, target_b.detach())

                    # Log losses to wandb
                    wandb.log({"Loss/Model_1": loss_1.item(), "Loss/Model_2": loss_2.item()}, step=total_steps)

                    self.optimizer_1.zero_grad()
                    loss_1.backward()
                    self.optimizer_1.step()

                    self.optimizer_2.zero_grad()
                    loss_2.backward()
                    self.optimizer_2.step()

                    if episode_steps % 4 == 0:
                        soft_update(self.target_model_1, self.model_1)
                        soft_update(self.target_model_2, self.model_2)

            # === Kết thúc episode ===
            scores.append(episode_reward)
            recent_scores.append(episode_reward)
            avg_score = np.mean(recent_scores)

            # Log score and epsilon to wandb
            wandb.log({"Score": episode_reward, "Epsilon": epsilon}, step=episode)

            # === Lưu model tốt nhất ===
            if episode_reward > best_score:
                best_score = episode_reward
                best_model_path = f"{result_dir}/best_model_ep{episode}_score{best_score:.2f}.pt"

                # Tạo thư mục models nếu chưa có
                os.makedirs("models", exist_ok=True)

                # Lưu cả hai model vào folder models/
                torch.save(self.model_1.state_dict(), f"models/best_model_1.pt")
                torch.save(self.model_2.state_dict(), f"models/best_model_2.pt")

                # Lưu bản tổng hợp (cả 2 model + thông tin)
                torch.save({
                    'model_1': self.model_1.state_dict(),
                    'model_2': self.model_2.state_dict(),
                    'score': best_score,
                    'episode': episode
                }, best_model_path)

            # === Ghi log CSV ===
            episode_time = time.time() - episode_start_time
            with open(csv_path, "a", newline="") as f:
                writer_csv = csv.writer(f)
                writer_csv.writerow([episode, episode_reward, epsilon, episode_steps, f"{episode_time:.2f}"])

            # === In tiến trình ===
            print(f"Episode {episode:03d}/{episodes-1} | "
                f"Score: {episode_reward:6.2f} | "
                f"Avg(10): {avg_score:6.2f} | "
                f"Eps: {epsilon:5.3f} | "
                f"Steps: {episode_steps:4d} | "
                f"Time: {episode_time:5.1f}s")

            if epsilon > min_epsilon:
                epsilon *= epsilon_decay

        # === Lưu kết quả ===
        # Create and log the training curve plot to wandb
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.set_title("Training Progress")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Score")
        ax.plot(scores, color='orange')
        plt.savefig(f"{result_dir}/training_curve.png")
        wandb.log({"Training Curve": wandb.Image(fig)})
        plt.close(fig)

        # Finish wandb run
        wandb.finish()

        print(f"\nTraining hoàn tất! Best Score = {best_score:.2f}")
        print(f"Model tốt nhất: {best_model_path}")
        print(f"Kết quả được lưu trong: {result_dir}")