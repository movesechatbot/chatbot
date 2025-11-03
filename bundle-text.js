#!/usr/bin/env node
/**
 * Junta arquivos de texto/código do projeto em um único arquivo,
 * com separadores contendo caminho e tamanho do arquivo.
 * Agora inclui suporte a lista de arquivos/padrões a serem ignorados manualmente.
 *
 * Uso:
 *   node bundle-text.js --root . --out TEXTAO.txt --maxKB 500
 */

const fs = require('fs');
const fsp = fs.promises;
const path = require('path');

// === CONFIGURAÇÃO MANUAL DE ARQUIVOS A PULAR ===========================
const SKIP_FILES = [
  // Exemplos — altere conforme quiser:
  'README.md',
  '/chatbot/dev-utils/base_faq.json',
  '.env',
  'conversa_1.txt',
  'conversa_2.txt',
  'conversa_3.txt',
  'conversa_4.txt',
  'conversa_5.txt',
  'conversa_6.txt',
  'base_faq.json',
  '__pycache__/app.cpython-313.pyc',
  '__pycache__/config.cpython-313.pyc',
  '__pycache__/kb.cpython-313.pyc',
  '__pycache__/llm.cpython-313.pyc',
  '__pycache__/playbook.cpython-313.pyc',
  '__pycache__/whatsapp.cpython-313.pyc',
  'Texto de treinamento/vendas.txt',
  // pode ser apenas parte do caminho
  // ou nome exato do arquivo
];
// =======================================================================

const argv = (() => {
  const a = process.argv.slice(2);
  const out = {};
  for (let i = 0; i < a.length; i++) {
    const k = a[i];
    if (k.startsWith('--')) {
      const key = k.slice(2);
      const val =
        i + 1 < a.length && !a[i + 1].startsWith('--') ? a[++i] : true;
      out[key] = val;
    }
  }
  return out;
})();

const ROOT = path.resolve(argv.root || '.');
const OUT = path.resolve(argv.out || 'PROJECT_BUNDLE.txt');
const MAX_KB = parseInt(argv.maxKB || '600', 10);
const MAX_BYTES = MAX_KB * 1024;

const TEXT_EXT = new Set([
  '.js',
  '.jsx',
  '.ts',
  '.tsx',
  '.mjs',
  '.cjs',
  '.php',
  '.html',
  '.htm',
  '.css',
  '.scss',
  '.sass',
  '.json',
  '.jsonc',
  '.md',
  '.markdown',
  '.txt',
  '.yaml',
  '.yml',
  '.env',
  '.env.example',
  '.gitignore',
  '.gitattributes',
  '.py',
  '.rb',
  '.go',
  '.rs',
  '.java',
  '.kt',
  '.c',
  '.h',
  '.cpp',
  '.hpp',
  '.cs',
  '.sql',
  '.sh',
  '.bat',
  '.ps1',
  '.ini',
  '.conf',
  '.toml',
  '.twig',
  '.blade.php',
  '.ejs',
  '.hbs',
]);

const IGNORE_DIRS = new Set([
  'node_modules',
  '.git',
  'vendor',
  'dist',
  'build',
  '.next',
  '.cache',
  '.turbo',
  '.parcel-cache',
  'coverage',
  '.idea',
  '.vscode',
  'storage',
  'logs',
  'tmp',
  '.nuxt',
  '.angular',
  'out',
  '.expo',
  '.gradle',
  'target',
]);

const IGNORE_FILES = new Set([
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
  'composer.lock',
  '.DS_Store',
]);

const IGNORE_EXT = new Set([
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.avif',
  '.bmp',
  '.ico',
  '.pdf',
  '.zip',
  '.rar',
  '.7z',
  '.tar',
  '.gz',
  '.mp3',
  '.wav',
  '.flac',
  '.mp4',
  '.mov',
  '.mkv',
  '.woff',
  '.woff2',
  '.ttf',
  '.eot',
  '.obj',
  '.fbx',
  '.glb',
  '.gltf',
]);

function looksTextByExt(file) {
  const ext = path.extname(file).toLowerCase();
  if (IGNORE_EXT.has(ext)) return false;
  if (TEXT_EXT.has(ext)) return true;
  return ext === '' ? true : false;
}

// === NOVA FUNÇÃO: checa se o arquivo deve ser pulado ===================
function shouldSkip(filePath) {
  const relPath = path.relative(ROOT, filePath).replace(/\\/g, '/');
  return SKIP_FILES.some((pattern) => relPath.includes(pattern));
}
// =======================================================================

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
  return new Date().toISOString();
}

async function main() {
  const files = [];
  for await (const fp of walk(ROOT)) {
    if (shouldSkip(fp)) continue; // 👈 nova verificação
    if (!looksTextByExt(fp)) continue;
    try {
      const st = await fsp.stat(fp);
      if (st.size > MAX_BYTES) continue;
      files.push({ fp, size: st.size });
    } catch {}
  }

  files.sort((a, b) => rel(a.fp).localeCompare(rel(b.fp)));

  const lines = [];
  lines.push('# BUNDLE DO PROJETO');
  lines.push(`# Gerado em: ${nowISO()}`);
  lines.push(`# Raiz: ${ROOT}`);
  lines.push(`# Arquivos incluídos: ${files.length}`);
  lines.push('');
  lines.push('## ÍNDICE');
  files.forEach((f, i) => {
    lines.push(
      `${String(i + 1).padStart(3, ' ')}. ${rel(f.fp)} (${f.size} bytes)`
    );
  });
  lines.push('\n---\n');

  for (const f of files) {
    const relative = rel(f.fp);
    const ext = path.extname(relative).toLowerCase();
    const fenceLang = (() => {
      if (['.js', '.jsx', '.mjs', '.cjs'].includes(ext)) return 'javascript';
      if (['.ts', '.tsx'].includes(ext)) return 'typescript';
      if (ext === '.php' || ext === '.blade.php') return 'php';
      if (['.css', '.scss', '.sass'].includes(ext)) return 'css';
      if (['.html', '.htm'].includes(ext)) return 'html';
      if (['.md', '.markdown'].includes(ext)) return 'md';
      if (['.json', '.jsonc'].includes(ext)) return 'json';
      if (['.yml', '.yaml'].includes(ext)) return 'yaml';
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

    lines.push('```' + fenceLang);
    lines.push(content.replace(/\uFEFF/g, ''));
    lines.push('```');
    lines.push(`\n/* ================================ END FILE ============================ */\n`);
  }

  await fsp.writeFile(OUT, lines.join('\n'), 'utf8');
  console.log(`✅ Gerado: ${OUT}`);
  console.log(`   Arquivos agregados: ${files.length}`);
  console.log(`   Tamanho máx. por arquivo: ${MAX_KB} KB`);
  console.log(`   Raiz: ${ROOT}`);
}

main().catch((err) => {
  console.error('Erro:', err);
  process.exit(1);
});
