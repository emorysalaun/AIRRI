# AttackWrapperSMOO.py

"""
SMOO (Sparse Multi-Objective Optimization Attack) Wrapper
"""

import numpy as np
import torch
import os

from .MOAA.MOAA import Attack
from .LossFunctions import UnTargeted
from utils.data_utils import (
    dataloader_to_tensor,
    tensor_to_numpy as TensorToNumpyHWC,
    numpy_to_tensor as NumpyHWCToTensor,
    tensor_to_dataloader,
)


def SMOO_AttackWrapper(model, device, dataLoader, config):
    """
    SMOO Attack Wrapper - runs sparse multi-objective optimization attack.
    
    Args:
        model: PyTorch model to attack
        device: torch device
        dataLoader: DataLoader with clean samples
        config: dict with attack parameters
    
    Returns:
        advLoader: DataLoader with adversarial samples
    """

    # Fix Random Seed for reproducibility
    seed = config.get("seed", 42)
    np.random.seed(seed)
    
    # Extract config parameters with defaults
    eps = config.get("eps", 20)
    iterations = config.get("iterations", 5000)
    pc = config.get("pc", 0.1)
    pm = config.get("pm", 0.4)
    pop_size = config.get("pop_size", 2)
    save_directory = config.get("save_directory", "./smoo_results")
    
    os.makedirs(save_directory, exist_ok=True)
    
    # Convert dataLoader to tensors, then to numpy HWC (using utils)
    xTensor, yTensor = dataloader_to_tensor(dataLoader)
    x_test, y_test = TensorToNumpyHWC(xTensor, yTensor)
    
    num_samples = len(x_test)
    print(f"\nSMOO Attack: {num_samples} samples, eps(k)={eps}, iterations={iterations}")
    print(f"Parameters: pc={pc}, pm={pm}, pop_size={pop_size}")
    
    # Track statistics
    all_adv_images = []
    all_labels_list = []
    successful_attacks = 0
    total_attacks = 0
    all_l0_norms = []
    all_l2_norms = []
    
    # Attack each image
    for i in range(num_samples):
        print(f"\n  Sample {i + 1}/{num_samples}: ", end="")
        
        original = x_test[i]
        label = int(y_test[i])
        
        loss = UnTargeted(model, label, to_pytorch=True)
        
        params = {
            "x": original,
            "eps": eps,
            "iterations": iterations,
            "pc": pc,
            "pm": pm,
            "pop_size": pop_size,
            "zero_probability": 0.0,
            "include_dist": True,
            "max_dist": float('inf'),
            "p_size": 1.0,
            "tournament_size": 2,
            "save_directory": os.path.join(save_directory, f"img_{i}.npy")
        }
        
        attack = Attack(params)
        attack.attack(loss)
        
        results = np.load(params["save_directory"], allow_pickle=True).item()
        
        total_attacks += 1
        perturbed = results["front0_imgs"][0]
        queries = results.get("queries", iterations)
        
        all_adv_images.append(perturbed)
        all_labels_list.append(label)
        
        if results["success"]:
            successful_attacks += 1
            diff = perturbed - original
            l0_norm = np.sum(np.any(diff != 0, axis=-1))
            l2_norm = np.sqrt(np.sum(diff ** 2))
            all_l0_norms.append(l0_norm)
            all_l2_norms.append(l2_norm)
            print(f"SUCCESS | L0: {l0_norm}, L2: {l2_norm:.4f}, Queries: {queries}")
        else:
            print(f"FAILED | Queries: {queries}")
    
    # Print summary
    success_rate = 100 * successful_attacks / total_attacks if total_attacks > 0 else 0
    avg_l0 = np.mean(all_l0_norms) if all_l0_norms else 0
    avg_l2 = np.mean(all_l2_norms) if all_l2_norms else 0
    
    print("\n" + "=" * 60)
    print(f"SMOO Attack Summary:")
    print(f"  - Success Rate: {successful_attacks}/{total_attacks} ({success_rate:.2f}%)")
    print(f"  - Epsilon (L0 budget / k): {eps}")
    print(f"  - Average L0 norm: {avg_l0:.2f}")
    print(f"  - Average L2 norm: {avg_l2:.4f}")
    print("=" * 60)
    
    # Convert adversarial images back to tensor
    adv_images_np = np.array(all_adv_images)
    labels_np = np.array(all_labels_list)
    
    adv_images_tensor, labels_tensor = NumpyHWCToTensor(adv_images_np, labels_np)
    
    # Create adversarial DataLoader
    advLoader = tensor_to_dataloader(
        adv_images_tensor, 
        labels_tensor, 
        transforms=None, 
        batch_size=dataLoader.batch_size, 
        randomizer=None
    )
    
    return advLoader