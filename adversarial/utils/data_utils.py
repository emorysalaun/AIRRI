import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
import os

# =====================================================================
#  Tensor / DataLoader conversion helpers
# =====================================================================


class MyDataSet(torch.utils.data.Dataset):
    def __init__(self, x_tensor, y_tensor, transforms=None):
        self.x = x_tensor
        self.y = y_tensor
        self.transforms = transforms

    def __getitem__(self, index):
        if self.transforms is None:
            return (self.x[index], self.y[index])
        return (self.transforms(self.x[index]), self.y[index])

    def __len__(self):
        return len(self.x)


def DataLoaderToTensor(dataLoader):
    numSamples = len(dataLoader.dataset)
    sampleShape = GetOutputShape(dataLoader)
    xData = torch.zeros((numSamples,) + sampleShape)
    yData = torch.zeros(numSamples)
    sampleIndex = 0
    for input_batch, target_batch in dataLoader:
        batchSize = input_batch.shape[0]
        for j in range(batchSize):
            xData[sampleIndex] = input_batch[j]
            yData[sampleIndex] = target_batch[j]
            sampleIndex += 1
    return xData, yData


def TensorToDataLoader(xData, yData, transforms=None, batchSize=None, randomizer=None):
    if batchSize is None:
        batchSize = xData.shape[0]
    dataset = MyDataSet(xData, yData, transforms)
    if randomizer is None:
        return DataLoader(dataset=dataset, batch_size=batchSize, shuffle=False)
    train_sampler = torch.utils.data.RandomSampler(dataset)
    return DataLoader(
        dataset=dataset, batch_size=batchSize, sampler=train_sampler, shuffle=False
    )


def TensorToNumpy(x_tensor, y_tensor):
    x_numpy = x_tensor.cpu().numpy()
    x_numpy = x_numpy.transpose(0, 2, 3, 1)  # NCHW -> NHWC
    y_numpy = y_tensor.cpu().numpy().astype(np.int64)
    return x_numpy, y_numpy


def NumpyToTensor(x_numpy, y_numpy):
    x_numpy = x_numpy.transpose(0, 3, 1, 2)  # NHWC -> NCHW
    return torch.from_numpy(x_numpy).float(), torch.from_numpy(y_numpy).long()


def GetOutputShape(dataLoader):
    for input_batch, _ in dataLoader:
        return input_batch[0].shape


# =====================================================================
#  Validation / Prediction
# =====================================================================


def validateD(valLoader, model, device=None):
    model.eval()
    acc = 0
    with torch.no_grad():
        for input_batch, target in valLoader:
            if device is None:
                input_batch = input_batch.cuda()
            else:
                input_batch = input_batch.to(device)
            output = model(input_batch).float()
            for j in range(input_batch.shape[0]):
                if output[j].argmax(axis=0) == target[j]:
                    acc += 1
    return acc / float(len(valLoader.dataset))


def predictD(dataLoader, numClasses, model, device=None):
    numSamples = len(dataLoader.dataset)
    yPred = torch.zeros(numSamples, numClasses)
    model.eval()
    indexer = 0
    with torch.no_grad():
        for input_batch, _ in dataLoader:
            if device is None:
                inputVar = input_batch.cuda()
            else:
                inputVar = input_batch.to(device)
            output = model(inputVar).float()
            for j in range(input_batch.shape[0]):
                yPred[indexer] = output[j]
                indexer += 1
    return yPred


def GetCorrectlyIdentifiedSamplesBalanced(
    model, totalSamplesRequired, dataLoader, numClasses, device=None
):
    sampleShape = GetOutputShape(dataLoader)
    xData, yData = DataLoaderToTensor(dataLoader)

    if totalSamplesRequired % numClasses != 0:
        raise ValueError("totalSamplesRequired must be divisible by numClasses.")

    numSamplesPerClass = totalSamplesRequired // numClasses
    correctlyClassified = torch.zeros(
        (numClasses, numSamplesPerClass, sampleShape[0], sampleShape[1], sampleShape[2])
    )
    sanityCounter = torch.zeros(numClasses)
    yPred = predictD(dataLoader, numClasses, model, device)

    for i in range(xData.shape[0]):
        predictedClass = yPred[i].argmax(axis=0)
        trueClass = yData[i]
        saved = int(sanityCounter[int(trueClass)])
        if predictedClass == trueClass and saved < numSamplesPerClass:
            correctlyClassified[int(trueClass), saved] = xData[i]
            sanityCounter[int(trueClass)] += 1

    for c in range(numClasses):
        if sanityCounter[c] != numSamplesPerClass:
            raise ValueError(
                f"Not enough correctly predicted samples for class {c} "
                f"(got {int(sanityCounter[c])}, need {numSamplesPerClass})."
            )

    xCorrect = torch.zeros((totalSamplesRequired, *xData.shape[1:]))
    yCorrect = torch.zeros(totalSamplesRequired)
    idx = 0
    for c in range(numClasses):
        for j in range(numSamplesPerClass):
            xCorrect[idx] = correctlyClassified[c, j]
            yCorrect[idx] = c
            idx += 1

    return TensorToDataLoader(
        xCorrect,
        yCorrect,
        transforms=None,
        batchSize=dataLoader.batch_size,
        randomizer=None,
    )


# =====================================================================
#  Gradient helpers (used by L0 attacks)
# =====================================================================


def get_predictions(model, x_nat, y_nat, device):
    x = torch.from_numpy(x_nat).permute(0, 3, 1, 2).float().to(device)
    y = torch.from_numpy(y_nat).to(device)
    with torch.no_grad():
        output = model(x)
    return (output.max(dim=-1)[1] == y).cpu().numpy()


def get_predictions_and_gradients(model, x_nat, y_nat, device):
    x = torch.from_numpy(x_nat).permute(0, 3, 1, 2).float().to(device)
    x.requires_grad_(True)
    y = torch.from_numpy(y_nat).to(device)

    with torch.enable_grad():
        output = model(x)
        loss = dlr_loss(output, y).mean()

    grad = torch.autograd.grad(loss, x)[0]
    grad = grad.detach().permute(0, 2, 3, 1).cpu().numpy()
    pred = (output.detach().max(dim=-1)[1] == y).detach().cpu().numpy()
    return pred, grad


def dlr_loss(x, y):
    """Difference of Logits Ratio loss."""
    x_sorted, ind_sorted = x.sort(dim=1)
    ind = (ind_sorted[:, -1] == y).float()
    u = torch.arange(x.shape[0])
    return -(x[u, y] - x_sorted[:, -2] * ind - x_sorted[:, -1] * (1.0 - ind))


# =====================================================================
#  Misc
# =====================================================================


def GetDataBounds(dataLoader, device):
    """Find actual min/max pixel values in the dataset."""
    minVal, maxVal = float("inf"), float("-inf")
    for xData, _ in dataLoader:
        xData = xData.to(device)
        minVal = min(minVal, xData.min().item())
        maxVal = max(maxVal, xData.max().item())
    return minVal, maxVal


def print_per_class_robust_accuracy(all_labels, all_robust_acc):
    unique_labels = np.unique(all_labels)
    print(f"\n{'=' * 70}")
    print("Per-Class Robust Accuracy:")
    print(f"{'=' * 70}\n")
    for label in unique_labels:
        idx = all_labels == label
        total = np.sum(idx)
        robust = np.sum(all_robust_acc[idx])
        print(f"Class {int(label)}: {robust}/{total} = {robust / total:.4f}")
    print(f"{'=' * 70}\n")


import os
from torchvision.utils import save_image


def save_samples(loader, attack_name, base_folder="saved_samples", num_samples=10):
    output_dir = os.path.join(base_folder, attack_name)
    os.makedirs(output_dir, exist_ok=True)

    data_iter = iter(loader)
    images, labels = next(data_iter)
    count = min(num_samples, len(images))

    for i in range(count):
        filename = os.path.join(output_dir, f"sample_{i}_label_{int(labels[i])}.png")
        save_image(images[i], filename)

    return count, output_dir
