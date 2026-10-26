import { spawn, spawnSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const pipelineDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(pipelineDir, '../frontend');
const origin = 'http://127.0.0.1:5173';

/**
 * Render one perturbed PNG from a render configuration.
 * Any omitted perturbation uses the AIRRI page default.
 * @param {object} config
 * @param {string} config.text
 * @param {string} [config.outputPath]
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
 * @returns {Promise<string>} saved PNG path
 */
export async function render(config) {
	if (!config?.text) {
		throw new Error('config.text is required.');
	}

	const outputPath = path.resolve(
		config.outputPath ?? path.join(pipelineDir, 'results', 'perturbed.png')
	);
	const server = await ensureServer();
	const browser = await chromium.launch({ headless: true });

	try {
		const page = await browser.newPage({
			viewport: { width: 1200, height: 800 },
			deviceScaleFactor: 1
		});
		await page.goto(`${origin}/internal/render`, { waitUntil: 'domcontentloaded' });
		await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');

		const dataUrl = await page.evaluate((job) => {
			const draw = window.render;
			if (!draw) throw new Error('Render page is not ready.');
			return draw(job);
		}, { ...config, outputPath: undefined, width: config.width ?? 926 });

		await mkdir(path.dirname(outputPath), { recursive: true });
		const base64 = dataUrl.replace(/^data:image\/png;base64,/, '');
		await writeFile(outputPath, Buffer.from(base64, 'base64'));
		return outputPath;
	} finally {
		await browser.close();
		if (server) stopServer(server);
	}
}

async function ensureServer() {
	if (await serverIsUp()) return null;

	const child = spawn('npm run dev -- --host 127.0.0.1 --port 5173 --strictPort', {
		cwd: frontendDir,
		shell: true,
		windowsHide: true
	});
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
		spawnSync(`taskkill /pid ${child.pid} /T /F`, { shell: true });
		return;
	}
	child.kill();
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isMain) {
	const config = {
		text: 'Topic: Our unit on language variation looks at how different dialects of English can differ in parts of their mental grammar. Write a paper about systematic differences between Standard American English and another dialect of English.',
		stripes: 0.45,
		stripeAngle: 30,
		stripeMode: 'global',
		perturbationColor: '#000000',
		outputPath: path.join(pipelineDir, 'results', 'perturbed.png')
	};

	const saved = await render(config);
	console.log(saved);
}
