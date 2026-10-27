import cv2
import torch
from torchvision import transforms
from live_parking_system import ParkingSlotCNN, MASK_PATH, CNN_MODEL_PATH

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
model = ParkingSlotCNN().to(device)
model.load_state_dict(torch.load(str(CNN_MODEL_PATH), map_location=device))
model.eval()

cap = cv2.VideoCapture(r'C:\Users\kesha\Downloads\parking_crop_loop.mp4')
ret, frame = cap.read()
cap.release()

if ret:
    mask_img = cv2.imread(str(MASK_PATH), cv2.IMREAD_GRAYSCALE)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_img)
    slot_boxes = [stats[i][:4] for i in range(1, num_labels)]

    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((32, 32)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    slot_tensors = [transform(cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2RGB)) for x, y, w, h in slot_boxes]
    batch = torch.stack(slot_tensors).to(device)
    preds = torch.argmax(model(batch), dim=1).cpu().numpy()

    free = sum(1 for p in preds if p == 0)
    occ = sum(1 for p in preds if p == 1)
    print(f'SUCCESS! Total Slots = {len(preds)}, Free = {free}, Occupied = {occ}')
    for i, p in enumerate(preds):
        status_str = "FREE (Green)" if p == 0 else "OCCUPIED (Red)"
        print(f'  Slot S{i+1}: {status_str}')
