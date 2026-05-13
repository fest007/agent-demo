#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const version = process.argv[2]?.trim();

if (!version || !/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(version)) {
  console.error("Usage: node scripts/bump-version.mjs <version>");
  console.error("Example: node scripts/bump-version.mjs 0.2.0");
  process.exit(1);
}

const files = [
  path.join(root, "agent-demo-web", "package.json"),
  path.join(root, "agent-demo-web", "src-tauri", "Cargo.toml"),
  path.join(root, "agent-demo-web", "src-tauri", "tauri.conf.json"),
  path.join(root, "agent-demo-agent", "pyproject.toml"),
  path.join(root, "agent-demo-server", "pyproject.toml"),
];

function write(file, content) {
  fs.writeFileSync(file, content, "utf8");
  console.log(`updated ${path.relative(root, file)}`);
}

write(path.join(root, "VERSION"), `${version}\n`);

for (const file of files) {
  const content = fs.readFileSync(file, "utf8");
  if (file.endsWith("package.json") || file.endsWith("tauri.conf.json")) {
    const json = JSON.parse(content);
    json.version = version;
    write(file, `${JSON.stringify(json, null, 2)}\n`);
    continue;
  }
  write(file, content.replace(/^version = ".*"$/m, `version = "${version}"`));
}

console.log(`version bumped to ${version}`);
