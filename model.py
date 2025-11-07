import torch
import torch.nn as nn
import torch.nn.functional as F

# ZombieNet
# 4 CNN
# 3 FC layers
# Output = action dim (0, 0, 1, 0, 0 , 0) 


class ZombieNet(nn.Module):
    def __init__(self, action_dim, hidden_dim=1024, dropout = 0, observation_shape=None):
        super(ZombieNet, self).__init__()

        # Convolutional Layers 
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=8, kernel_size=4, stride=2)
        self.conv2 = nn.Conv2d(in_channels=8, out_channels=16, kernel_size=4, stride=2)
        self.conv3 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=2)
        self.conv4 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, stride=2)

        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        conv_output_size = self.calculate_conv_output(observation_shape)
        print("conv_output_size: ", conv_output_size)

        # Fully Connected Layers
        self.fc1 = nn.Linear(conv_output_size, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.output = nn.Linear(hidden_dim, action_dim)

        self.dropout = dropout

        self.apply(self.weights_init)


    def weights_init(self, m):
        if isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.Linear):
            nn.init.xavier_normal_(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)


    def calculate_conv_output(self, observation_shape):
        x = torch.zeros(1, *observation_shape)
        x = self.pool(F.relu(self.conv1(x)))
        x = F.relu(self.conv2(x))
        x = self.pool(F.relu(self.conv3(x)))
        x = F.relu(self.conv4(x))

        return x.view(-1).shape[0]

    def forward(self, x):
        x = x / 255

        x = self.pool(F.relu(self.conv1(x)))
        x = F.relu(self.conv2(x))
        x = self.pool(F.relu(self.conv3(x)))
        x = F.relu(self.conv4(x))

        x = x.view(x.size(0), -1)

        x = F.relu(self.fc1(x))

        if self.dropout > 0:
            x = F.dropout(x, p=self.dropout)
        
        x = F.relu(self.fc2(x))
        
        if self.dropout > 0:
            x = F.dropout(x, p=self.dropout)

        x = F.relu(self.fc3(x))

        output = self.output(x)

        return output
    
    def save_the_model(self, filename='models/latest.pt'):
        torch.save(self.state_dict(), filename)

    def load_the_model(self, filename='models/latest.pt'):
        """Load model weights from `filename`.

        This helper will try to load weights that were saved on GPU even when
        running on a CPU-only machine by using `map_location=torch.device('cpu')`.
        It handles missing files and reports errors clearly.
        """
        try:
            # If CUDA is not available, map tensors to CPU when loading.
            if not torch.cuda.is_available():
                state = torch.load(filename, map_location=torch.device('cpu'))
            else:
                state = torch.load(filename)

            self.load_state_dict(state)
            print(f"Loaded weights from filename {filename}")

        except FileNotFoundError:
            print(f"No weights file found at {filename}")
        except RuntimeError as e:
            # Handle CUDA->CPU deserialization errors more gracefully
            msg = str(e)
            if 'Attempting to deserialize object on a CUDA device' in msg and not torch.cuda.is_available():
                try:
                    state = torch.load(filename, map_location=torch.device('cpu'))
                    self.load_state_dict(state)
                    print(f"Loaded weights (forced to CPU) from filename {filename}")
                except Exception as e2:
                    print(f"Failed to load weights from {filename}: {e2}")
            else:
                print(f"Failed to load weights from {filename}: {e}")
        except Exception as e:
            print(f"Unexpected error while loading weights from {filename}: {e}")


def soft_update(target, source, tau=0.005):
    for target_param, param in zip(target.parameters(), source.parameters()):
        target_param.data.copy_(target_param.data * (1.0 - tau) + param.data * tau)

def hard_update(target, source):
    for target_param, param in zip(target.parameters(), source.parameters()):
        target_param.data.copy_(param.data)

