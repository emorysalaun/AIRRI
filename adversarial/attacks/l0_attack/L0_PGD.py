import numpy as np
import torch

from utils.data_utils import (
    DataLoaderToTensor,
    TensorToNumpy,
    NumpyToTensor,
    TensorToDataLoader,
    get_predictions,
)
from . import L0_Utils


def L0_PGD_AttackWrapper(
    model, device, dataLoader, n_restarts, num_steps, step_size, sparsity, random_start
):
    model.eval()

    if random_start and n_restarts > 1:
        raise ValueError(
            f"Invalid: random_start={random_start} with n_restarts={n_restarts}. "
            f"Use n_restarts=1 with random_start=True, or random_start=False."
        )

    total_samples = len(dataLoader.dataset)

    x_tensor, y_tensor = DataLoaderToTensor(dataLoader)
    all_original_examples, all_labels = TensorToNumpy(x_tensor, y_tensor)

    all_adv_examples = np.copy(all_original_examples)
    all_latest_attempts = np.copy(all_original_examples)
    pgd_adv_acc = None

    for counter in range(n_restarts):
        print(f"Restart {counter + 1}/{n_restarts}")

        if counter == 0:
            corr_pred = get_predictions(
                model, all_original_examples, all_labels, device
            )
            pgd_adv_acc = np.copy(corr_pred)

        batch_start_idx = 0
        for batch_idx, (x_batch, y_batch) in enumerate(dataLoader):
            x_numpy, y_numpy = TensorToNumpy(x_batch, y_batch)
            batch_size = x_numpy.shape[0]
            batch_end_idx = batch_start_idx + batch_size

            x_nat = all_original_examples[batch_start_idx:batch_end_idx]
            y_nat = all_labels[batch_start_idx:batch_end_idx]

            x_batch_adv, curr_pgd_adv_acc = L0_Utils.perturb_L0_box(
                model,
                x_nat,
                y_nat,
                -x_nat,
                1.0 - x_nat,
                sparsity,
                num_steps,
                step_size,
                device,
                random_start,
            )

            pgd_adv_acc[batch_start_idx:batch_end_idx] = np.minimum(
                pgd_adv_acc[batch_start_idx:batch_end_idx], curr_pgd_adv_acc
            )

            mask = np.logical_not(curr_pgd_adv_acc)
            all_adv_examples[batch_start_idx:batch_end_idx][mask] = x_batch_adv[mask]
            all_latest_attempts[batch_start_idx:batch_end_idx] = x_batch_adv

            batch_start_idx = batch_end_idx

    still_robust = pgd_adv_acc.astype(bool)
    all_adv_examples[still_robust] = all_latest_attempts[still_robust]

    overall_robust_acc = np.sum(pgd_adv_acc) / total_samples
    pixels_changed = np.sum(
        np.amax(np.abs(all_adv_examples - all_original_examples) > 1e-10, axis=-1),
        axis=(1, 2),
    )
    max_perturbation = np.amax(np.abs(all_adv_examples - all_original_examples))

    print(f"{'=' * 70}")
    print(f"Total samples processed: {total_samples}")
    print(f"Overall Robust Accuracy at {sparsity} pixels: {overall_robust_acc:.4f}")
    print(f"Maximum perturbation size: {max_perturbation:.5f}")
    print(f"{'=' * 70}\n")

    xAdv, yClean = NumpyToTensor(all_adv_examples, all_labels)
    advLoader = TensorToDataLoader(
        xAdv, yClean, transforms=None, batchSize=dataLoader.batch_size, randomizer=None
    )
    return advLoader
