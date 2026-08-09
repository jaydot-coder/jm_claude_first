# mcp — 세법 조사용 MCP 서버

이 저장소에서 Claude Code로 세법을 조사할 때 쓰는 MCP 서버 설정입니다. 서버 목록은 저장소
루트의 `.mcp.json`에 커밋되어 있으므로, **다른 PC에서는 저장소를 clone하고 인증키만 넣으면
그대로 붙습니다.**

지금 붙는 서버는 하나입니다.

| 서버 | 원본 | 담당 |
|------|------|------|
| `korean-law` | 법제처 국가법령정보센터 OPEN API (`open.law.go.kr`) | 법령 조문 원문 — 국세기본법·소득세법·법인세법·부가가치세법·조특법의 법률/시행령/시행규칙, 법원 판례, 행정규칙, 조세심판례를 포함한 18개 도메인 결정문 |

패키지는 [`korean-law-mcp`](https://github.com/chrisryugj/korean-law-mcp) (MIT)이고, 법제처
공식 OPEN API를 그대로 읽어오므로 조문 원문에 관한 한 이보다 정확한 경로는 없습니다.

결론을 쓰기 전에는 `legal_analysis(mode=verify_citations)`를 태우세요. 인용한 조문이 실존하는지
법제처 DB에 되짚어 확인해주는 도구인데, 세법 상담에서 환각이 제일 위험한 지점이 지어낸
조문·사건번호라 이 한 단계가 값을 합니다.

## 새 PC에서 준비하기

Node.js 20 이상이 필요합니다. 서버는 `npx`가 알아서 받아 실행하므로 따로 설치할 건 없습니다.

### 1. 법제처 인증키(OC) 발급

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

### 2. 서버 승인

저장소 루트에서 `claude`를 실행하면 처음 한 번 워크스페이스 신뢰(trust)와 프로젝트 MCP 서버
사용 승인을 묻습니다. 승인하면 `.claude/settings.json`의 `enabledMcpjsonServers` 설정이 적용되어
이후로는 자동으로 붙습니다.

`claude mcp list`로 연결을 확인할 수 있습니다.

## 버전 올리기

`.mcp.json`에 `korean-law-mcp@4.9.6`으로 버전을 못박아 두었습니다. 법령 DB를 다루는 도구라
"어제는 되던 게 오늘 다르게 나오는" 상황을 피하는 쪽을 택했고, 대신 올릴 때는 수동입니다.

```bash
npm view korean-law-mcp version    # 최신 버전 확인 후 .mcp.json의 숫자를 고쳐 씁니다
```

## 알아둘 것

- **비공식 클라이언트입니다.** 법적 효력이 필요한 판단은 국가법령정보센터 원문을 직접 확인하고
  세무사 검토를 거쳐야 합니다. 패키지 README도 같은 경고를 답니다.
- 법제처 OPEN API는 클라우드 IP를 막는 경우가 있습니다. 집·사무실 PC에서는 문제없지만, 원격
  개발 환경에서 403이 뜬다면 인증키 문제가 아니라 IP 차단일 수 있습니다.
- 도구 호출이 법제처를 여러 번 오가느라 느릴 수 있어 `.mcp.json`에서 타임아웃을 180초로
  올려두었습니다.

## 나중에 국세청 자료까지 필요해지면

법제처 API에는 **국세청 해석례(질의회신)·기본통칙·홈택스 상담사례**가 없습니다. 조문과 판례로
답이 안 나오고 국세청이 실제로 어떻게 회신했는지가 필요해지는 시점이 오면, 그때
[`taxlaw-nts-mcp`](https://github.com/kim-go-chon/taxlaw-nts-mcp)를 보조로 붙이면 됩니다.
지금 넣지 않은 이유는 신생 비공식 클라이언트라 검증이 덜 됐고, 국세법령정보시스템에 공식
오픈 API가 없어 사이트를 직접 조회하는 방식이라 차단 위험과 이용약관 준수 부담이 따라오기
때문입니다.

붙일 때 미리 알아둘 것 — 실제로 확인한 내용입니다:

- npm에 배포돼 있지 않아 GitHub 커밋 SHA로 받아 빌드해야 합니다. `npx github:...`는 npm 10에서
  `GitFetcher requires an Arborist constructor` 오류로 실패하니, `package.json`에 git 의존성으로
  적고 `npm ci`로 설치해야 합니다.
- 그 `package.json`에 `"overrides": { "typescript": "5.9.3" }`이 필요합니다. 없으면 설치 시점에
  따라 TypeScript 6.x가 잡혀 `moduleResolution=node10` 오류로 빌드가 깨집니다.
- `github:` 축약형을 쓰면 락파일이 ssh URL로 잠기는데, GitHub SSH 키가 없는 PC에서도 npm이
  https로 자동 폴백해 정상 설치됩니다.
- STDIO 전용이라 claude.ai 웹에서는 못 쓰고 PC의 Claude Code나 Claude Desktop에서만 됩니다.
- 붙이는 순서는 **`korean-law`로 조문을 먼저 확정하고 → 해석례·통칙으로 보완**입니다. 이건
  `taxlaw-nts` 서버가 스스로 안내하는 순서이기도 합니다.
