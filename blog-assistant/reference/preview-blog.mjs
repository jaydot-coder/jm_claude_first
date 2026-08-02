#!/usr/bin/env node
/**
 * preview-blog.mjs
 * 마크다운 블로그 파일을 네이버 블로그용 HTML로 변환하고 브라우저 미리보기를 엽니다.
 *
 * 사용법: node scripts/preview-blog.mjs output/파일명.md
 *
 * 지원 문법 (기본 마크다운 외 추가):
 *   ==텍스트==  →  노란 배경 강조 (background-color: #FFE400)
 */

import { readFileSync, writeFileSync } from "fs";
import { resolve, basename } from "path";
import { tmpdir } from "os";
import { exec } from "child_process";

// ─────────────────────────────────────────────
// ✏️  커스터마이징 설정 (여기만 수정하면 됩니다)
// ─────────────────────────────────────────────
const CONFIG = {
  // 텍스트 가운데 정렬 (true / false)
  centerAlign: true,

  // 인용구(>) 처리 방식: "blockquote"(기본 박스) | "bold"(볼드 텍스트만)
  blockquoteStyle: "bold",

  // 제목 크기: "normal"(#→h1, ##→h2) | "small"(#→h3 크기, ##→h4 크기)
  headingSize: "small",

  // 노란 배경 강조색 (==텍스트== 문법)
  highlightColor: "#FFE400",
};
// ─────────────────────────────────────────────

// 전역 설치된 패키지 로드
const PKG_PATH =
  "C:/Users/jamin/AppData/Roaming/npm/node_modules/@jjlabsio/md-to-naver-blog/dist/index.js";

const mdFilePath = process.argv[2];
if (!mdFilePath) {
  console.error("사용법: node scripts/preview-blog.mjs output/파일명.md");
  process.exit(1);
}

const absPath = resolve(mdFilePath);
const markdown = readFileSync(absPath, "utf-8");

// 패키지 로드
const { convert } = await import(`file:///${PKG_PATH}`);

// 변환
let { title, html } = convert(markdown);

// ── 후처리 1: ==텍스트== → 노란 배경 강조
html = html.replace(
  /==(.+?)==/g,
  `<span style="background-color:${CONFIG.highlightColor};">$1</span>`
);

// ── 후처리 2: 인용구 처리
if (CONFIG.blockquoteStyle === "bold") {
  // <div style="border-left: ..."><p>내용</p></div> → <p><strong>내용</strong></p>
  html = html.replace(
    /<div style="border-left:[^"]*"[^>]*>\s*<p>([\s\S]*?)<\/p>\s*<\/div>/g,
    (_, inner) => `<p><strong style="font-weight:bold;">${inner}</strong></p>`
  );
}

// ── 후처리 3: 제목 크기 축소 (h1→h3 수준, h2→h4 수준)
if (CONFIG.headingSize === "small") {
  html = html
    .replace(/<h1 style="font-size:\s*2em;([^"]*)">/g, '<h1 style="font-size:1.2em;$1">')
    .replace(/<h2 style="font-size:\s*1\.5em;([^"]*)">/g, '<h2 style="font-size:1.1em;$1">');
}

// ── 후처리 4: 가운데 정렬
if (CONFIG.centerAlign) {
  html = html
    .replace(/<p(?:\s[^>]*)?>/g, (tag) => {
      if (tag.includes("text-align")) return tag;
      return tag.replace("<p", '<p style="text-align:center;"');
    })
    .replace(/<h([1-6]) style="([^"]*)"/g, (_, level, styles) => {
      if (styles.includes("text-align")) return _;
      return `<h${level} style="${styles}; text-align:center;"`;
    });
}

// 미리보기 HTML 페이지 생성
const previewHtml = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>블로그 미리보기: ${title || basename(absPath)}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", sans-serif; background: #f5f5f5; }
    .toolbar {
      position: sticky; top: 0; z-index: 100;
      background: #03C75A; color: white;
      padding: 12px 24px; display: flex; align-items: center; gap: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .toolbar h1 { font-size: 15px; font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .copy-btn {
      background: white; color: #03C75A;
      border: none; border-radius: 6px;
      padding: 8px 20px; font-size: 14px; font-weight: 700;
      cursor: pointer; transition: all 0.15s;
    }
    .copy-btn:hover { background: #e6f9ef; }
    .copy-btn.copied { background: #e6f9ef; color: #017a3a; }
    .guide {
      background: #fffbe6; border: 1px solid #ffe066;
      border-radius: 8px; margin: 16px 24px; padding: 12px 16px;
      font-size: 13px; color: #856404; line-height: 1.6;
    }
    .guide strong { color: #5c4500; }
    .preview-wrap {
      max-width: 720px; margin: 0 auto; padding: 24px;
    }
    .preview-box {
      background: white; border-radius: 8px;
      padding: 32px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      line-height: 1.8; font-size: 15px; color: #222;
    }
    .preview-box h1 { font-size: 2em; font-weight: bold; margin-bottom: 1em; }
    .preview-box h2 { font-size: 1.5em; font-weight: bold; margin: 1em 0 0.5em; }
    .preview-box h3 { font-size: 1.2em; font-weight: bold; margin: 1em 0 0.5em; }
    .preview-box p { margin-bottom: 0.5em; }
    .toast {
      position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%);
      background: #222; color: white; padding: 12px 24px;
      border-radius: 24px; font-size: 14px; font-weight: 500;
      opacity: 0; transition: opacity 0.3s; pointer-events: none;
    }
    .toast.show { opacity: 1; }
  </style>
</head>
<body>
  <div class="toolbar">
    <h1>📝 ${title || basename(absPath)}</h1>
    <button class="copy-btn" onclick="copyHtml()">서식 복사</button>
  </div>
  <div class="guide">
    <strong>네이버 블로그 붙여넣기 방법:</strong>
    위 <strong>[서식 복사]</strong> 버튼 클릭 →
    네이버 블로그 에디터 열기 →
    <strong>Ctrl+V</strong> 붙여넣기 →
    이미지 자리(<code style="background:#f4f4f4;padding:1px 4px;border-radius:3px;">[이미지: ...]</code>)에 직접 이미지 삽입
  </div>
  <div class="preview-wrap">
    <div class="preview-box" id="content">
      ${html}
    </div>
  </div>
  <div class="toast" id="toast">클립보드에 복사됐습니다!</div>

  <script>
    const htmlContent = document.getElementById('content').innerHTML;

    async function copyHtml() {
      try {
        await navigator.clipboard.write([
          new ClipboardItem({
            'text/html': new Blob([htmlContent], { type: 'text/html' }),
            'text/plain': new Blob([document.getElementById('content').innerText], { type: 'text/plain' }),
          })
        ]);
        showToast();
        const btn = document.querySelector('.copy-btn');
        btn.textContent = '✓ 복사됨';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = '서식 복사'; btn.classList.remove('copied'); }, 2000);
      } catch (e) {
        // fallback
        const el = document.createElement('div');
        el.innerHTML = htmlContent;
        document.body.appendChild(el);
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand('copy');
        sel.removeAllRanges();
        document.body.removeChild(el);
        showToast();
      }
    }

    function showToast() {
      const t = document.getElementById('toast');
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 2500);
    }
  </script>
</body>
</html>`;

// 임시 파일 저장 후 브라우저 열기
const tmpFile = resolve(tmpdir(), `naver-blog-preview-${Date.now()}.html`);
writeFileSync(tmpFile, previewHtml, "utf-8");

// OS별 브라우저 열기
const openCmd =
  process.platform === "win32"
    ? `start "" "${tmpFile}"`
    : process.platform === "darwin"
    ? `open "${tmpFile}"`
    : `xdg-open "${tmpFile}"`;

exec(openCmd, (err) => {
  if (err) {
    console.error(`브라우저를 자동으로 열지 못했습니다. 직접 열어주세요: ${tmpFile}`);
  } else {
    console.log(`\n✅ 미리보기가 브라우저에서 열렸습니다`);
    console.log(`   파일: ${absPath}`);
    console.log(`   [서식 복사] 버튼 클릭 → 네이버 블로그에 Ctrl+V\n`);
  }
});
