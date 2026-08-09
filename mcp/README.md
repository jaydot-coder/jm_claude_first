# mcp — 세법 조사용 MCP 서버

이 저장소에서 Claude Code로 세법을 조사할 때 쓰는 MCP 서버 설정입니다. 서버 목록은 저장소
루트의 `.mcp.json`에 커밋되어 있으므로, **다른 PC에서는 저장소를 clone하고 아래 준비 두 가지만
하면 그대로 붙습니다.**

## 왜 두 개인가

세법은 자료가 두 층으로 나뉘어 있고, 한쪽만으로는 답이 반쪽이 됩니다.

| 서버 | 원본 | 담당 |
|------|------|------|
| `korean-law` | 법제처 국가법령정보센터 OPEN API (`open.law.go.kr`) | 법령 조문 원문 — 국세기본법·소득세법·법인세법·부가가치세법·조특법의 법률/시행령/시행규칙, 법원 판례, 행정규칙 |
| `taxlaw-nts` | 국세법령정보시스템 (`taxlaw.nts.go.kr`) | 실무 판단 — 국세청 해석례(질의회신), 기본통칙, 조세심판례, 홈택스 상담사례, 시점별 조문·부칙·조문 diff |

`taxlaw-nts` 서버가 스스로 안내하는 순서도 **`korean-law`로 조문을 먼저 확정하고 → 해석례·통칙으로
보완**입니다. 두 서버 모두 인용한 사건번호가 실존하는지 되짚는 검증 도구
(`korean-law`의 `legal_analysis(mode=verify_citations)`, `taxlaw-nts`의 `verify_nts_citations`)를
갖고 있는데, 세법 상담에서 환각이 제일 위험한 지점이라 결론 쓰기 전에 꼭 태우는 게 좋습니다.

## 새 PC에서 준비하기

### 1. 법제처 인증키(OC) 발급 — `korean-law`에 필요

<https://open.law.go.kr/LSO/openApi/guideList.do> 에서 신청하면 `honggildong` 같은 인증키(OC)가
나옵니다. 무료이고, 발급받은 본인만 쓸 수 있습니다.

받은 키를 `LAW_OC` 환경변수로 넣어둡니다. `.mcp.json`은 이 값을 `${LAW_OC}`로 읽어가므로
**키가 저장소에 커밋되지 않습니다.**

Windows PowerShell (영구 등록, 등록 후 터미널을 새로 열어야 적용됩니다):

```powershell
setx LAW_OC "발급받은키"
```

macOS / Linux — `~/.zshrc` 또는 `~/.bashrc`에 추가:

```bash
export LAW_OC=발급받은키
```

### 2. `taxlaw-nts` 빌드 — Node.js 20 이상 필요

이 서버는 npm에 배포되어 있지 않아서, 커밋 SHA로 고정해둔 소스를 한 번 받아 빌드해야 합니다.
저장소 루트에서:

```bash
npm ci --prefix mcp
```

PowerShell도 같은 한 줄입니다. `mcp/package-lock.json`에 커밋 SHA와 의존성 트리가 잠겨 있어
어느 PC에서 받아도 같은 버전이 빌드됩니다. 결과물은 `mcp/node_modules/`에 들어가고 gitignore
대상입니다. GitHub SSH 키가 없는 PC에서도 npm이 자동으로 https로 받아옵니다.

### 3. 서버 승인

준비가 끝난 뒤 저장소 루트에서 `claude`를 실행하면 처음 한 번 워크스페이스 신뢰(trust)와
프로젝트 MCP 서버 사용 승인을 묻습니다. 승인하면 `.claude/settings.json`의
`enabledMcpjsonServers` 설정이 적용되어 이후로는 자동으로 붙습니다.

`claude mcp list`로 두 서버가 연결됐는지 확인할 수 있습니다.

## 버전 올리기

둘 다 버전을 고정해두었습니다. 법령 DB를 다루는 도구라 "어제는 되던 게 오늘 다르게 나오는"
상황을 피하는 쪽을 택했고, 대신 올릴 때는 수동입니다.

`korean-law` — 최신 버전을 확인하고 `.mcp.json`의 `korean-law-mcp@4.9.6`을 고쳐 씁니다:

```bash
npm view korean-law-mcp version
```

`taxlaw-nts` — <https://github.com/kim-go-chon/taxlaw-nts-mcp> 의 최신 커밋 SHA로
`mcp/package.json`의 `#` 뒤를 바꾼 뒤 `npm install --prefix mcp`로 락파일을 갱신합니다.

`mcp/package.json`의 `overrides.typescript`는 지워도 되나 싶을 수 있는데, 없으면 설치 시점에
따라 TypeScript 6.x가 잡혀 `moduleResolution=node10` 오류로 빌드가 깨집니다. 그대로 두세요.

## 알아둘 것

- **두 서버 모두 비공식 클라이언트입니다.** 법적 효력이 필요한 판단은 국가법령정보센터·국세청
  원문을 직접 확인하고 세무사 검토를 거쳐야 합니다. 두 프로젝트 README도 같은 경고를 답니다.
- `taxlaw-nts`는 국세법령정보시스템에 공식 오픈 API가 없어 사이트를 직접 조회하는 방식입니다.
  국세청 이용약관과 `robots.txt` 준수는 사용자 책임이고, 과도한 호출은 차단될 수 있습니다.
- `taxlaw-nts`는 STDIO 전용이라 claude.ai 웹에서는 쓸 수 없습니다. PC의 Claude Code나
  Claude Desktop에서만 동작합니다. `korean-law`는 웹에서도 커스텀 커넥터로 붙일 수 있습니다.
- 두 서버의 도구 호출은 외부 사이트를 여러 번 오가느라 느릴 수 있어 `.mcp.json`에서 타임아웃을
  180초로 올려두었습니다(`taxlaw-nts` 자체 예산이 90초).

## 출처

- `korean-law` — <https://github.com/chrisryugj/korean-law-mcp> (MIT)
- `taxlaw-nts` — <https://github.com/kim-go-chon/taxlaw-nts-mcp> (MIT)
