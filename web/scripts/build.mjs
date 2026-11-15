import { build } from "esbuild";
import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { themes } from "../src/themes.js";

const root = fileURLToPath(new URL("../", import.meta.url));
const dist = join(root, "dist");
const require = createRequire(import.meta.url);
await mkdir(join(dist, "fonts"), { recursive: true });
await build({ entryPoints: { "access-kit": join(root, "src/index.js"), auto: join(root, "src/auto.js") }, outdir: dist, bundle: true, format: "esm", target: "es2022", sourcemap: true, splitting: true });
function declarations(theme) {
  return `color-scheme:${theme.scheme};${Object.entries(theme).filter(([key]) => !["label", "scheme"].includes(key)).map(([key, value]) => `--ak-color-${key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`)}:${value};`).join("")}`;
}
const palettes = [
  `:root{${declarations(themes.light)}}`,
  ...Object.entries(themes).map(([name, theme]) => `[data-ak-theme="${name}"]{${declarations(theme)}}`),
  `@media(prefers-color-scheme:dark){:root:not([data-ak-theme]){${declarations(themes.dark)}}}`,
].join("\n");
const fonts = [];
for (const [name, family] of [["atkinson-hyperlegible", "AK Atkinson"], ["noto-sans", "AK Noto Sans"]]) {
  const packageRoot = dirname(require.resolve(`@fontsource/${name}/package.json`));
  for (const weight of [400, 700]) {
    let css = await readFile(join(packageRoot, `${weight}.css`), "utf8");
    css = css.replace(/font-family:\s*['"][^'"]+['"]/g, `font-family: '${family}'`);
    for (const match of css.matchAll(/url\(['"]?\.\/files\/([^)'"]+)['"]?\)/g)) await cp(join(packageRoot, "files", match[1]), join(dist, "fonts", match[1]));
    fonts.push(css.replaceAll("./files/", "./fonts/"));
  }
  await cp(join(packageRoot, "LICENSE"), join(dist, "fonts", `${name}.LICENSE`));
}
const base = await readFile(join(root, "src/styles/base.css"), "utf8");
await writeFile(join(dist, "access-kit.css"), `${fonts.join("\n")}\n${palettes}\n${base}`);
console.log("Built ESM modules, five themes, base CSS, and local OFL font assets.");
