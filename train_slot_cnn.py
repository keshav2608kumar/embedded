"""
Smart Parking System - Train Custom PyTorch Deep Learning CNN on Parking Slot Crops
Trains on 6,090 images in ai/dataset/archive/parking/clf-data/ (empty & not_empty)
"""

import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from pathlib import Path

DATA_DIR = Path("ai/dataset/archive/parking/clf-data")
SAVE_PATH = Path("ai/models/slot_cnn.pt")

class ParkingSlotCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 16x16
            
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 8x8
            
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)) # 4x4
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(64 * 4 * 4, 64),
            nn.ReLU(),
            nn.Linear(64, 2) # 0: empty, 1: not_empty
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)

def main():
    print("[INFO] Starting fast PyTorch CNN training on RTX 3050 GPU...")
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device} ({torch.cuda.get_device_name(0)})")

    transform = transforms.Compose([
        transforms.Resize((32, 32)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    dataset = datasets.ImageFolder(str(DATA_DIR), transform=transform)
    print(f"[INFO] Dataset classes: {dataset.class_to_idx} (Total samples: {len(dataset)})")
    
    train_size = int(0.85 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=128, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_set, batch_size=128, shuffle=False, num_workers=0)

    model = ParkingSlotCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    t0 = time.time()
    for epoch in range(5):
        model.train()
        total_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        # Quick eval
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, preds = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (preds == labels).sum().item()
                
        val_acc = correct / total * 100
        print(f"Epoch {epoch+1}/5 - Loss: {total_loss/len(train_loader):.4f} - Val Accuracy: {val_acc:.2f}%", flush=True)

    train_time = time.time() - t0
    print(f"[SUCCESS] Training complete in {train_time:.1f} seconds!", flush=True)
    
    SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(SAVE_PATH))
    print(f"[SUCCESS] Trained model saved to: {SAVE_PATH}")

if __name__ == "__main__":
    main()
