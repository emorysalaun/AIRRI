import numpy as np
import torch
from torch.utils.data import DataLoader

class SimpleDataset(torch.utils.data.Dataset):
    """A simple PyTorch dataset wrapper around x and y tensors."""
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


def dataloader_to_tensor(dataloader):
    """Converts a DataLoader to PyTorch tensors for inputs and targets."""
    num_samples = len(dataloader.dataset)
    
    # Get the shape of a single sample
    for input_batch, _ in dataloader:
        sample_shape = input_batch[0].shape
        break
        
    x_data = torch.zeros((num_samples,) + sample_shape)
    y_data = torch.zeros(num_samples)
    sample_index = 0
    for input_batch, target_batch in dataloader:
        batch_size = input_batch.shape[0]
        for j in range(batch_size):
            x_data[sample_index] = input_batch[j]
            y_data[sample_index] = target_batch[j]
            sample_index += 1
    return x_data, y_data


def tensor_to_dataloader(x_data, y_data, transforms=None, batch_size=None, randomizer=None):
    """Converts PyTorch tensors back into a DataLoader."""
    if batch_size is None:
        batch_size = x_data.shape[0]
    dataset = SimpleDataset(x_data, y_data, transforms)
    if randomizer is None:
        return DataLoader(dataset=dataset, batch_size=batch_size, shuffle=False)
    train_sampler = torch.utils.data.RandomSampler(dataset)
    return DataLoader(
        dataset=dataset, batch_size=batch_size, sampler=train_sampler, shuffle=False
    )


def tensor_to_numpy(x_tensor, y_tensor):
    """Converts PyTorch tensors (NCHW) to NumPy arrays (NHWC)."""
    x_numpy = x_tensor.cpu().numpy()
    x_numpy = x_numpy.transpose(0, 2, 3, 1)  # NCHW -> NHWC
    y_numpy = y_tensor.cpu().numpy().astype(np.int64)
    return x_numpy, y_numpy


def numpy_to_tensor(x_numpy, y_numpy):
    """Converts NumPy arrays (NHWC) to PyTorch tensors (NCHW)."""
    x_numpy = x_numpy.transpose(0, 3, 1, 2)  # NHWC -> NCHW
    return torch.from_numpy(x_numpy).float(), torch.from_numpy(y_numpy).long()


def get_predictions(model, x_nat, y_nat, device):
    """Gets model predictions and checks correctness against targets."""
    x = torch.from_numpy(x_nat).permute(0, 3, 1, 2).float().to(device)
    y = torch.from_numpy(y_nat).to(device)
    with torch.no_grad():
        output = model(x)
    return (output.max(dim=-1)[1] == y).cpu().numpy()


def get_predictions_and_gradients(model, x_nat, y_nat, device):
    """Gets model predictions and gradients of DLR loss with respect to inputs."""
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
