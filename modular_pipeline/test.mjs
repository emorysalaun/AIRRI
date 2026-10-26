
import { render } from './render.mjs';

const config = {
    stripes: 0.45,
    stripeAngle: 30,
    stripeMode: 'global',
    perturbationColor: '#000000'
};

const assignments = [
    'This is the first assignment.',
    'This is the second assignment.',
    'This is the third assignment.'
];

for (let i = 0; i < assignments.length; i++) {
    const outputPath = `results/assignment_${i + 1}.png`;

    const saved = await render(
        assignments[i],
        config,
        outputPath
    );

    console.log(`Saved: ${saved}`);
}
