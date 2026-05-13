#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const version = fs.readFileSync(path.join(root, "VERSION"), "utf8").trim();
const outDir = path.join(root, "dist-release", "bundle");

const skipDirs = new Set([
  ".git",
  ".github",
  ".venv",
  "__pycache__",
  ".pytest_cache",
  "node_modules",
  "data",
  "dist-release",
  "test-artifacts",
  "playwright-report",
  "test-results",
]);
const skipFilePatterns = [/^\.env($|\.)/, /\.db$/, /\.sqlite$/, /tsconfig\.tsbuildinfo$/];

const include = [
  "VERSION",
  "README.md",
  "STARTUP.md",
  "RELEASE.md",
  "技术方案.md",
  "docker-compose.yml",
  "scripts",
  "agent-demo-agent",
  "agent-demo-server",
  "agent-demo-web",
];

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    if (skipDirs.has(path.basename(src))) {
      return;
    }
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
    return;
  }
  if (skipFilePatterns.some((pattern) => pattern.test(path.basename(src)))) {
    return;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });

for (const entry of include) {
  const src = path.join(root, entry);
  if (fs.existsSync(src)) {
    copyRecursive(src, path.join(outDir, entry));
  }
}

const manifest = {
  name: "agent-demo",
  version,
  builtAt: new Date().toISOString(),
  runnerOS: process.env.RUNNER_OS || process.platform,
  node: process.version,
};
fs.writeFileSync(path.join(outDir, "release-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`prepared release bundle ${version} at ${path.relative(root, outDir)}`);
