import numpy as np
import torch
import math


def pytorch_switch(tensor_image):
    return tensor_image.permute(1, 2, 0)


def to_pytorch(tensor_image):
    return torch.from_numpy(tensor_image).permute(2, 0, 1).float()

def get_device():
    """Get the device (CUDA if available, else CPU)"""
    return torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class UnTargeted:
    def __init__(self, model, true, unormalize=False, to_pytorch=False):
        self.model = model
        self.true = true
        self.unormalize = unormalize
        self.to_pytorch = to_pytorch
        self.device = get_device() # get device

    def get_label(self, img):
        if self.unormalize:
            img_ = img * 255.

        else:
            img_ = img

        if self.to_pytorch:
            img_ = to_pytorch(img_)
            img_ = img_[None, :]
            img_ = img_.to(self.device) # move to correct device
            preds = self.model(img_).flatten()
            y = int(torch.argmax(preds))
        else:
            preds = self.model(np.expand_dims(img_, axis=0)).flatten()
            y = int(np.argmax(preds))

        return y

    def __call__(self, img):

        if self.unormalize:
            img_ = img * 255.

        else:
            img_ = img

        if self.to_pytorch:
            img_ = to_pytorch(img_)
            img_ = img_[None, :]
            img_ = img_.to(self.device) # move to correct device
            preds = self.model(img_).flatten()
            y = int(torch.argmax(preds))
            preds = preds.tolist()
        else:
            preds = self.model(np.expand_dims(img_, axis=0)).flatten()
            y = int(np.argmax(preds))

        is_adversarial = True if y != self.true else False

        f_true = math.log(math.exp(preds[self.true]) + 1e-30)
        preds[self.true] = -math.inf

        f_other = math.log(math.exp(max(preds)) + 1e-30)
        return [is_adversarial, float(f_true - f_other)]


class Targeted:
    def __init__(self, model, true, target, unormalize=False, to_pytorch=False):
        self.model = model
        self.true = true
        self.target = target
        self.unormalize = unormalize
        self.to_pytorch = to_pytorch
        self.device = get_device() # get device

    def get_label(self, img):
        if self.unormalize:
            img_ = img * 255.

        else:
            img_ = img

        if self.to_pytorch:
            img_ = to_pytorch(img_)
            img_ = img_[None, :]
            img_ = img_.to(self.device) # move to correct device
            preds = self.model(img_).flatten()
            y = int(torch.argmax(preds))
        else:
            preds = self.model(np.expand_dims(img_, axis=0)).flatten()
            y = int(np.argmax(preds))

        return y

    def __call__(self, img):

        if self.unormalize:
            img_ = img * 255.

        else:
            img_ = img

        if self.to_pytorch:
            img_ = to_pytorch(img_)
            img_ = img_[None, :]
            img_ = img_.to(self.device) # move to correct device
            preds = self.model(img_).flatten()
            y = int(torch.argmax(preds))
            preds = preds.tolist()
        else:
            preds = self.model(np.expand_dims(img_, axis=0)).flatten()
            y = int(np.argmax(preds))

        is_adversarial = True if y == self.target else False
        #print("current label %d target label %d" % (y, self.target))
        f_target = preds[self.target]
        #preds[self.true] = -math.inf

        f_other = math.log(sum(math.exp(pi) for pi in preds))
        return [is_adversarial, f_other - f_target]