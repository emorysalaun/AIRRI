
import { spawn, spawnSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath} from 'node:url';
import { chromium } from 'playwright';

const pipelineDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(pipelineDir, '../frontend');
const origin = 'http://127.0.0.1:5173';

/**
 * Render one perturbed PNG using assignment text and an AIRRI configuration.
 * Any omitted perturbation uses the AIRRI page default.
 *
 * @param {string} text - Assignment text to render.
 * @param {object} config - AIRRI rendering configuration.
 * @param {number} [config.seed]
 * @param {number} [config.noise]
 * @param {number} [config.stripes]
 * @param {number} [config.fontSize]
 * @param {number} [config.lineSpacing]
 * @param {number} [config.charSpacing]
 * @param {number} [config.wordSpacing]
 * @param {string} [config.perturbationColor]
 * @param {number} [config.stripeAngle]
 * @param {'global' | 'between-lines'} [config.stripeMode]
 * @param {number} [config.opacityJitter]
 * @param {number} [config.width]
 * @param {string} [outputPath] - Destination PNG path.
 * @returns {Promise<string>} Saved PNG path.
 */
export async function render(text, config = {}, outputPath) {
    if (typeof text !== 'string' || !text.trim()) {
        throw new Error('Assignment text is required.');
    }

    const resolvedOutputPath = path.resolve(
        outputPath ?? path.join(pipelineDir, 'results', 'perturbed.png')
    );

    const server = await ensureServer();
    let browser;

    try {
        browser = await chromium.launch({ headless: true });

        const page = await browser.newPage({
            viewport: { width: 1200, height: 800 },
            deviceScaleFactor: 1
        });

        await page.goto(`${origin}/internal/render`, {
            waitUntil: 'domcontentloaded'
        });

        await page.waitForFunction(
            () => document.documentElement.dataset.ready === 'true'
        );

        const dataUrl = await page.evaluate((job) => {
            const draw = window.render;
            if (!draw) throw new Error('Render page is not ready.');
            return draw(job);
        }, {
            ...config,
            text,
            width: config.width ?? 926
        });

        await mkdir(path.dirname(resolvedOutputPath), {
            recursive: true
        });

        const base64 = dataUrl.replace(/^data:image\/png;base64,/, '');

        await writeFile(
            resolvedOutputPath,
            Buffer.from(base64, 'base64')
        );

        return resolvedOutputPath;
    } finally {
        if (browser) await browser.close();
        if (server) stopServer(server);
    }
}

async function ensureServer() {
    if (await serverIsUp()) return null;

    const child = spawn(
        'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
        {
            cwd: frontendDir,
            shell: true,
            windowsHide: true
        }
    );

    const started = Date.now();

    while (Date.now() - started < 60000) {
        if (await serverIsUp()) return child;
        await new Promise((resolve) => setTimeout(resolve, 400));
    }

    stopServer(child);
    throw new Error('Frontend did not start. From frontend, run: npm run dev');
}

async function serverIsUp() {
    try {
        const response = await fetch(`${origin}/internal/render`);
        return response.ok;
    } catch {
        return false;
    }
}

function stopServer(child) {
    if (!child?.pid || child.exitCode !== null) return;

    if (process.platform === 'win32') {
        spawnSync(`taskkill /pid ${child.pid} /T /F`, {
            shell: true
        });
        return;
    }

    child.kill();
}
