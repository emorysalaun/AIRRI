import { render } from './render.mjs';
import { configs } from './configs.mjs';
import { assignments } from './assignments.mjs';
import { writeFile, mkdir } from 'node:fs/promises';

const manifest = [];

await mkdir('results', { recursive: true });

for (const config of configs) {
    const { id: configId, ...renderConfig } = config;

    for (const assignment of assignments) {
        const imageName = `${configId}_${assignment.assignment_name}.png`;
        const outputPath = `results/${imageName}`;

        const saved = await render(
            assignment.ground_truth,
            renderConfig,
            outputPath
        );

        manifest.push({
            image_name: imageName,
            ground_truth: assignment.ground_truth
        });

        console.log(`Saved: ${saved}`);
    }
}

await writeFile(
    'results/manifest.json',
    JSON.stringify(manifest, null, 2),
    'utf8'
);