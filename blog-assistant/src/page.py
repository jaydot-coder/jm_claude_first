"""Builds the single-file preview page.

Everything is inlined (thumbnails as data URIs, no external CSS/JS) so the result is one
portable .html the user can open on the PC or drop into Drive and open on a phone.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

from src.image_slots import ImageSlot, SlotResolution
from src.markdown_naver import ConvertResult, replace_slots
from src.photos import thumbnail_data_uri


@dataclass
class RenderedPage:
    html: str
    exported_names: dict[int, str]  # slot index -> exported jpeg filename


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _preview_slot_html(slot: ImageSlot, data_uri: str | None) -> str:
    if slot.photo is None:
        return (
            '<div style="border:2px dashed #e05252;border-radius:8px;padding:16px;'
            'margin:12px 0;color:#b03030;font-size:14px;text-align:center;">'
            f"⚠ 사진 {slot.number} — {_esc(slot.problem or '사진 없음')}"
            f"<br><span style=\"color:#888;font-size:13px;\">{_esc(slot.caption)}</span>"
            "</div>"
        )
    caption = _esc(slot.caption) or "(설명 없음)"
    return (
        '<figure style="margin:16px 0;text-align:center;">'
        f'<img src="{data_uri}" alt="{caption}" '
        'style="max-width:100%;height:auto;border-radius:6px;" />'
        '<figcaption style="font-size:13px;color:#888;margin-top:6px;">'
        f"사진 {slot.number} · {caption}"
        "</figcaption>"
        "</figure>"
    )


def _copy_slot_html(slot: ImageSlot) -> str:
    """What lands in the clipboard. Naver will not accept our local images, so the copied
    text carries a visible marker the user replaces with the real photo in the editor.

    Slots with no photo are labelled differently on purpose: there is no numbered file to
    insert for them, so reusing "사진 N" would point at a file that does not exist.
    """
    if slot.photo is None:
        label = "[사진 없음" + (f": {slot.caption}" if slot.caption else "") + "]"
    else:
        label = f"[사진 {slot.number}" + (f": {slot.caption}" if slot.caption else "") + "]"
    return f'<p style="text-align:center;color:#888;">{_esc(label)}</p>'


def _photo_list_html(resolution: SlotResolution, thumbs: dict[int, str], exported: dict[int, str]) -> str:
    rows = []
    for slot in resolution.slots:
        if slot.photo is None:
            continue
        exported_name = exported.get(slot.index, "")
        rows.append(
            '<li style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;'
            'border-bottom:1px solid #eee;">'
            f'<div style="flex:0 0 34px;font-weight:700;font-size:15px;color:#03C75A;">'
            f"{slot.number}</div>"
            f'<img src="{thumbs[slot.index]}" alt="" '
            'style="flex:0 0 84px;width:84px;height:84px;object-fit:cover;border-radius:6px;" />'
            '<div style="flex:1;min-width:0;font-size:13px;line-height:1.6;">'
            f'<div style="color:#222;">{_esc(slot.caption) or "(설명 없음)"}</div>'
            f'<div style="color:#03C75A;font-family:monospace;word-break:break-all;">'
            f"{_esc(exported_name)}</div>"
            f'<div style="color:#aaa;font-family:monospace;word-break:break-all;">'
            f"원본: {_esc(slot.photo.name)}</div>"
            "</div></li>"
        )
    if not rows:
        return '<p style="color:#888;font-size:14px;">배치된 사진이 없습니다.</p>'
    return f'<ol style="list-style:none;padding:0;margin:0;">{"".join(rows)}</ol>'


def _warnings_html(resolution: SlotResolution) -> str:
    blocks = []
    if resolution.problems:
        items = "".join(
            f"<li>사진 {s.number}: {_esc(s.problem or '')}"
            f'{f" — {_esc(s.caption)}" if s.caption else ""}</li>'
            for s in resolution.problems
        )
        blocks.append(
            '<div style="background:#fdecea;border:1px solid #f5c6c2;border-radius:8px;'
            'padding:12px 16px;margin:12px 0;font-size:13px;color:#b03030;">'
            f"<strong>확인 필요</strong><ul style=\"margin:6px 0 0 18px;\">{items}</ul></div>"
        )
    if resolution.unused_photos:
        items = "".join(
            f'<li style="font-family:monospace;">{_esc(p.name)}</li>'
            for p in resolution.unused_photos
        )
        blocks.append(
            '<div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;'
            'padding:12px 16px;margin:12px 0;font-size:13px;color:#8a6d00;">'
            f"<strong>글에 안 쓰인 사진 {len(resolution.unused_photos)}장</strong>"
            f'<ul style="margin:6px 0 0 18px;">{items}</ul></div>'
        )
    return "".join(blocks)


def build_page(
    converted: ConvertResult,
    resolution: SlotResolution,
    exported: dict[int, str],
    source_name: str,
) -> str:
    thumbs = {
        slot.index: thumbnail_data_uri(slot.photo)
        for slot in resolution.slots
        if slot.photo is not None
    }

    preview_body = replace_slots(
        converted.body_html,
        lambda i: _preview_slot_html(resolution.slots[i], thumbs.get(i)),
    )
    copy_body = replace_slots(
        converted.body_html, lambda i: _copy_slot_html(resolution.slots[i])
    )

    title = converted.title or source_name
    photo_count = len(resolution.filled)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>블로그 미리보기: {_esc(title)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
         background: #f5f5f5; color: #222; }}
  .toolbar {{ position: sticky; top: 0; z-index: 100; background: #03C75A; color: #fff;
             padding: 12px 16px; display: flex; align-items: center; gap: 12px;
             box-shadow: 0 2px 8px rgba(0,0,0,.15); }}
  .toolbar h1 {{ font-size: 15px; font-weight: 600; flex: 1; overflow: hidden;
                text-overflow: ellipsis; white-space: nowrap; }}
  .copy-btn {{ background: #fff; color: #03C75A; border: 0; border-radius: 6px;
              padding: 9px 18px; font-size: 14px; font-weight: 700; cursor: pointer;
              white-space: nowrap; }}
  .copy-btn.copied {{ background: #e6f9ef; color: #017a3a; }}
  .wrap {{ max-width: 760px; margin: 0 auto; padding: 16px; }}
  .guide {{ background: #fffbe6; border: 1px solid #ffe066; border-radius: 8px;
           padding: 12px 16px; font-size: 13px; color: #856404; line-height: 1.7; }}
  .guide code {{ background: #f4f4f4; padding: 1px 5px; border-radius: 3px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 20px; margin-top: 16px;
          box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .card h2.section {{ font-size: 14px; color: #666; font-weight: 700; margin-bottom: 12px;
                     letter-spacing: .02em; }}
  .post {{ line-height: 1.9; font-size: 15px; }}
  .post p {{ margin-bottom: .5em; }}
  .post hr {{ border: 0; border-top: 1px solid #eee; margin: 1.4em 0; }}
  .post img {{ max-width: 100%; height: auto; }}
  .toast {{ position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
           background: #222; color: #fff; padding: 12px 22px; border-radius: 24px;
           font-size: 14px; opacity: 0; transition: opacity .3s; pointer-events: none; }}
  .toast.show {{ opacity: 1; }}
  #copy-source {{ display: none; }}
</style>
</head>
<body>
<div class="toolbar">
  <h1>📝 {_esc(title)}</h1>
  <button class="copy-btn" onclick="copyPost()">서식 복사</button>
</div>

<div class="wrap">
  <div class="guide">
    <strong>네이버에 올리는 순서</strong><br>
    1. <strong>[서식 복사]</strong> → 네이버 블로그 에디터에서 <strong>붙여넣기</strong><br>
    2. 글 안의 <code>[사진 N]</code> 자리마다 아래 목록의 <strong>N번 사진</strong>을 삽입<br>
    3. 삽입한 뒤 <code>[사진 N]</code> 글자는 지우기<br>
    사진 파일은 <code>{_esc(source_name)}_images/</code> 폴더에 삽입 순서대로 번호가 붙어 있습니다.
  </div>

  {_warnings_html(resolution)}

  <div class="card">
    <h2 class="section">미리보기 · 사진 {photo_count}장</h2>
    <div class="post">{preview_body}</div>
  </div>

  <div class="card">
    <h2 class="section">사진 삽입 순서</h2>
    {_photo_list_html(resolution, thumbs, exported)}
  </div>
</div>

<div id="copy-source">{copy_body}</div>
<div class="toast" id="toast">클립보드에 복사됐습니다</div>

<script>
  async function copyPost() {{
    const source = document.getElementById('copy-source');
    const btn = document.querySelector('.copy-btn');
    try {{
      await navigator.clipboard.write([new ClipboardItem({{
        'text/html': new Blob([source.innerHTML], {{ type: 'text/html' }}),
        'text/plain': new Blob([source.innerText], {{ type: 'text/plain' }}),
      }})]);
    }} catch (e) {{
      // Older browsers / non-secure contexts: fall back to a selection-based copy.
      const holder = document.createElement('div');
      holder.innerHTML = source.innerHTML;
      document.body.appendChild(holder);
      const range = document.createRange();
      range.selectNodeContents(holder);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      document.execCommand('copy');
      sel.removeAllRanges();
      document.body.removeChild(holder);
    }}
    btn.textContent = '✓ 복사됨';
    btn.classList.add('copied');
    setTimeout(() => {{ btn.textContent = '서식 복사'; btn.classList.remove('copied'); }}, 2000);
    const toast = document.getElementById('toast');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2200);
  }}
</script>
</body>
</html>"""
