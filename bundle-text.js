#!/usr/bin/env node
/**
 * Junta arquivos de texto/código do projeto em um único arquivo,
 * com separadores contendo caminho e tamanho do arquivo.
 *
 * Uso:
 *   node bundle-text.js --root . --out TEXTAO.txt --maxKB 500
 *   (todos os parâmetros são opcionais)
 */

const fs = require('fs');
const fsp = fs.promises;
const path = require('path');

const argv = (() => {
  const a = process.argv.slice(2);
  const out = {};
  for (let i = 0; i < a.length; i++) {
    const k = a[i];
    if (k.startsWith('--')) {
      const key = k.slice(2);
      const val = (i + 1 < a.length && !a[i + 1].startsWith('--')) ? a[++i] : true;
      out[key] = val;
    }
  }
  return out;
})();

const ROOT = path.resolve(argv.root || '.');
const OUT  = path.resolve(argv.out  || 'PROJECT_BUNDLE.txt');
const MAX_KB = parseInt(argv.maxKB || '600', 10); // pula arquivos > MAX_KB
const MAX_BYTES = MAX_KB * 1024;

// Whitelist de extensões consideradas texto/código
const TEXT_EXT = new Set([
  // web / node / php
  '.js','.jsx','.ts','.tsx','.mjs','.cjs',
  '.php','.html','.htm','.css','.scss','.sass',
  '.json','.jsonc','.md','.markdown','.txt',
  '.yaml','.yml','.env','.env.example',
  '.gitignore','.gitattributes',
  // outras linguagens comuns
  '.py','.rb','.go','.rs','.java','.kt','.c','.h','.cpp','.hpp','.cs',
  '.sql','.sh','.bat','.ps1','.ini','.conf','.toml',
  // templates / views
  '.twig','.blade.php','.ejs','.hbs'
]);

// Diretórios a ignorar
const IGNORE_DIRS = new Set([
  'node_modules','.git','vendor','dist','build','.next','.cache','.turbo',
  '.parcel-cache','coverage','.idea','.vscode','storage','logs','tmp','.nuxt',
  '.angular','out','.expo','.gradle','target'
]);

// Arquivos específicos a ignorar (grandes/ruidosos)
const IGNORE_FILES = new Set([
  'package-lock.json','yarn.lock','pnpm-lock.yaml','composer.lock',
  '.DS_Store'
]);

// Extensões explicitamente ignoradas (binários)
const IGNORE_EXT = new Set([
  '.png','.jpg','.jpeg','.gif','.webp','.avif','.bmp','.ico',
  '.pdf','.zip','.rar','.7z','.tar','.gz',
  '.mp3','.wav','.flac','.mp4','.mov','.mkv',
  '.woff','.woff2','.ttf','.eot',
  '.obj','.fbx','.glb','.gltf'
]);

function looksTextByExt(file) {
  const ext = path.extname(file).toLowerCase();
  if (IGNORE_EXT.has(ext)) return false;
  if (TEXT_EXT.has(ext)) return true;
  // fallback: trate sem extensão como texto pequeno
  return ext === '' ? true : false;
}

async function* walk(dir) {
  let entries;
  try {
    entries = await fsp.readdir(dir, { withFileTypes: true });
  } catch (e) {
    return;
  }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (IGNORE_DIRS.has(entry.name)) continue;
      yield* walk(full);
    } else if (entry.isFile()) {
      if (IGNORE_FILES.has(entry.name)) continue;
      yield full;
    }
  }
}

function rel(p) {
  return path.relative(ROOT, p).split(path.sep).join('/');
}

function nowISO() {
  const d = new Date();
  return d.toISOString();
}

async function main() {
  const files = [];
  for await (const fp of walk(ROOT)) {
    if (!looksTextByExt(fp)) continue;
    try {
      const st = await fsp.stat(fp);
      if (st.size > MAX_BYTES) continue;
      files.push({ fp, size: st.size });
    } catch {}
  }

  // Ordena alfabeticamente para previsibilidade
  files.sort((a,b) => rel(a.fp).localeCompare(rel(b.fp)));

  const lines = [];
  lines.push('# BUNDLE DO PROJETO');
  lines.push(`# Gerado em: ${nowISO()}`);
  lines.push(`# Raiz: ${ROOT}`);
  lines.push(`# Arquivos incluídos: ${files.length}`);
  lines.push('');
  lines.push('## ÍNDICE');
  files.forEach((f, i) => {
    lines.push(`${String(i+1).padStart(3,' ')}. ${rel(f.fp)} (${f.size} bytes)`);
  });
  lines.push('\n---\n');

  for (const f of files) {
    const relative = rel(f.fp);
    const ext = path.extname(relative).toLowerCase();
    const fenceLang = (() => {
      if (['.js','.jsx','.mjs','.cjs'].includes(ext)) return 'javascript';
      if (['.ts','.tsx'].includes(ext)) return 'typescript';
      if (ext === '.php' || ext === '.blade.php') return 'php';
      if (ext === '.css' || ext === '.scss' || ext === '.sass') return 'css';
      if (ext === '.html' || ext === '.htm') return 'html';
      if (ext === '.md' || ext === '.markdown') return 'md';
      if (ext === '.json' || ext === '.jsonc') return 'json';
      if (ext === '.yml' || ext === '.yaml') return 'yaml';
      if (ext === '.sh') return 'bash';
      if (ext === '.ps1') return 'powershell';
      if (ext === '.py') return 'python';
      if (ext === '.rb') return 'ruby';
      if (ext === '.sql') return 'sql';
      return '';
    })();

    lines.push(`\n/* ===================================================================== */`);
    lines.push(`/* START FILE: ${relative} | ${f.size} bytes */`);
    lines.push(`/* ===================================================================== */\n`);

    let content = '';
    try {
      content = await fsp.readFile(f.fp, 'utf8');
    } catch (e) {
      content = `<<ERRO AO LER ARQUIVO: ${e.message}>>`;
    }

    // Cerca com fence para ficar legível quando colar aqui no chat
    lines.push('```' + fenceLang);
    lines.push(content.replace(/\uFEFF/g, '')); // remove BOM se existir
    lines.push('```');

    lines.push(`\n/* ================================ END FILE ============================ */\n`);
  }

  await fsp.writeFile(OUT, lines.join('\n'), 'utf8');
  console.log(`✅ Gerado: ${OUT}`);
  console.log(`   Arquivos agregados: ${files.length}`);
  console.log(`   Tamanho máx. por arquivo: ${MAX_KB} KB`);
  console.log(`   Raiz: ${ROOT}`);
}

main().catch(err => {
  console.error('Erro:', err);
  process.exit(1);
});
