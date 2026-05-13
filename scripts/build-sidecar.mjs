#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const serverDir = path.join(root, "agent-demo-server");
const tauriBinDir = path.join(root, "agent-demo-web", "src-tauri", "binaries");

function run(command, args, options = {}) {
  console.log(`$ ${command} ${args.join(" ")}`);
  execFileSync(command, args, {
    cwd: options.cwd || root,
    stdio: "inherit",
    env: { ...process.env, ...options.env },
  });
}

function output(command, args, options = {}) {
  return execFileSync(command, args, {
    cwd: options.cwd || root,
    encoding: "utf8",
    env: { ...process.env, ...options.env },
  }).trim();
}

const rustInfo = output("rustc", ["-vV"]);
const hostLine = rustInfo.split("\n").find((line) => line.startsWith("host:"));
if (!hostLine) {
  throw new Error("Unable to detect Rust host triple from rustc -vV");
}
const triple = hostLine.replace("host:", "").trim();
const isWindows = process.platform === "win32";
const binaryName = `agent-demo-sidecar-${triple}${isWindows ? ".exe" : ""}`;
const sourceBinary = path.join(serverDir, "dist", `agent-demo-sidecar${isWindows ? ".exe" : ""}`);
const targetBinary = path.join(tauriBinDir, binaryName);

run("uv", ["sync", "--all-extras"], { cwd: serverDir });
run(
  "uv",
  [
    "run",
    "pyinstaller",
    "--clean",
    "--onefile",
    "--name",
    "agent-demo-sidecar",
    "--paths",
    "src",
    "--paths",
    "../agent-demo-agent/src",
    "src/server/desktop_sidecar.py",
  ],
  { cwd: serverDir },
);

fs.mkdirSync(tauriBinDir, { recursive: true });
fs.copyFileSync(sourceBinary, targetBinary);
fs.chmodSync(targetBinary, 0o755);
console.log(`sidecar copied to ${path.relative(root, targetBinary)}`);
