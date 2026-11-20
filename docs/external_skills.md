# 外部スキル一覧（Claude Agent Skills 100選 から追加）

スプレッドシート「Claude Agent Skills 100選」に載っている GitHub 公開スキルを `.claude/skills/` にコピーしたもの（2026-11-20 取得）。
すでに使えるスキル（Anthropic 公式・導入済みプラグイン）と重複するものは入れていない。

- 呼び方: Claude Code で `/スキル名`（例: `/brainstorming`）。または普通に頼めば、説明文に合うスキルが自動で選ばれる。
- 中身は英語のまま（原文を改変していない。名前の重複を避けるため phd-skills だけ `phd-` を付けた）。
- 取り込み時に、外部へ勝手に送信するコード・プロンプト注入・危険なコマンドが無いかを確認済み。外部APIに接続するのは脆弱性系（NVD/EPSS/CISA/MITRE の公開データ）と video-downloader（yt-dlp）だけ。
- 更新したいときは元リポジトリから同じフォルダを取り直す。

## ETERNAL向けに日本語化した版

| スキル | 元にした英語スキル（シートのNo） |
|---|---|
| `/eternal-copywriting` | copywriting（No.1） |
| `/eternal-line-broadcast` | email-campaigns（No.2） |
| `/eternal-note-research` | content-research-writer（No.4） |
| `/eternal-liver-success` | customer-success-manager（No.13） |

## 元のスキル一覧

| No | 分類 | シートのスキル名 | 追加したスキル（/呼び方） | こんな時に使う（シートより） | ライセンス | 出典 |
|---|---|---|---|---|---|---|
| 1 | マーケ・営業 | Marketing Skills for Claude Code | `/copywriting` | LPの改善案出しから広告コピー作成、SEO分析までを一気通貫で行い、マーケティング施策のPDCAを高速化するために使う。 | MIT | [GitHub](https://github.com/coreyhaines31/marketingskills/tree/HEAD/skills/copywriting) |
| 2 | マーケ・営業 | Email Campaigns Skill | `/email-campaigns` | HTMLメールの作成から配信までを自動化し、デザイン性の高いメルマガを専門知識なしで送るために使う。 | MIT | [GitHub](https://github.com/irinabuht12-oss/email-campaigns-claude) |
| 3 | マーケ・営業 | Lead Research Assistant Skill | `/lead-research-assistant` | 営業先の企業情報を自動でリサーチし、相手の課題に合わせた刺さる提案メッセージを自分で作成するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/lead-research-assistant) |
| 4 | マーケ・営業 | Content Research Writer Skill | `/content-research-writer` | ブログ記事の構成案作成や引用元の調査を自動化し、読者に役立つ高品質な記事を短時間で書くために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/content-research-writer) |
| 5 | マーケ・営業 | Brand Guidelines Skill | `/brand-guidelines` | 社内資料を作る際に、ブランドカラーやフォントを自動で適用させ、デザインの統一感を出す手間を省くために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/brand-guidelines) |
| 6 | マーケ・営業 | Competitive Ads Extractor Skill | `/competitive-ads-extractor` | 競合他社の広告を分析して、自社の広告で使うべきキャッチコピーや訴求ポイントのヒントを得るために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/competitive-ads-extractor) |
| 7 | マーケ・営業 | Domain Name Brainstormer Skill | `/domain-name-brainstormer` | Webサイト公開に必要なドメイン取得や初期設定を自動化し、新しいプロジェクトを素早く立ち上げるために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/domain-name-brainstormer) |
| 8 | マーケ・営業 | Twitter Algorithm Optimizer Skill | `/twitter-algorithm-optimizer` | SNSの投稿内容をターゲットに合わせて自動で最適化し、フォロワーからの反応を増やすために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/twitter-algorithm-optimizer) |
| 9 | マーケ・営業 | Sales Engineering Proposal Skill | `/sales-engineer` | ECサイトの商品紹介文を、SEOキーワードを盛り込みつつ魅力的な表現に一括で書き換えるために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/business-growth/skills/sales-engineer) |
| 10 | マーケ・営業 | Marketing Ops Skill | `/marketing-ops` | 過去の成功パターンを学習させ、新規顧客へのアプローチメールを相手ごとにパーソナライズするために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/marketing-skill/skills/marketing-ops) |
| 11 | マーケ・営業 | Advanced SEO Audit & Optimizer Skill | （追加なし: marketing:seo-audit（導入済みプラグイン）） | SEO業務をAI主導で効率化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | - | - |
| 12 | マーケ・営業 | Google Ads Campaign Builder Skill | `/paid-ads` | 広告運用者のキャンペーン作成時間を1/10に短縮の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/marketing-skill/skills/paid-ads) |
| 13 | マーケ・営業 | Customer Success Playbook Skill | `/customer-success-manager` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/business-growth/skills/customer-success-manager) |
| 14 | 文書・デザイン | UI/UX Pro Max Skill | `/ui-ux-pro-max` | マーケ部門のオペレーション効率化。施策運用の属人化を解消し、データドリブンな運用体制を構築。 | MIT | [GitHub](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/HEAD/.claude/skills/ui-ux-pro-max) |
| 15 | 文書・デザイン | Obsidian Skills | `/defuddle`<br>`/json-canvas`<br>`/knap`<br>`/obsidian-bases`<br>`/obsidian-cli`<br>`/obsidian-headless`<br>`/obsidian-markdown` | ナレッジベース構築・文書自動生成・Web抽出を自動化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/kepano/obsidian-skills/tree/HEAD/plugins/obsidian/skills/defuddle) |
| 16 | 文書・デザイン | PDF Skill (公式) | （追加なし: anthropic-skills:pdf） | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | - | - |
| 17 | 文書・デザイン | DOCX Skill (公式) | （追加なし: anthropic-skills:docx） | 提案書・報告書の自動化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | - | - |
| 18 | 文書・デザイン | XLSX Skill (公式) | （追加なし: anthropic-skills:xlsx） | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | - | - |
| 19 | 文書・デザイン | PPTX Skill (公式) | （追加なし: anthropic-skills:pptx） | プレゼン資料自動生成で営業・企画業務を加速の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | - | - |
| 20 | 文書・デザイン | Image Enhancer Skill | `/image-enhancer` | マーケ資料・プレゼンのビジュアルクオリティを即時向上の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/image-enhancer) |
| 21 | 文書・デザイン | Theme Factory Skill | （追加なし: anthropic-skills:theme-factory） | ブランド統一資料作成を一瞬で完了の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | - | - |
| 22 | 文書・デザイン | Canvas Design Skill | （追加なし: anthropic-skills:canvas-design） | マーケ・イベント資料のビジュアル作成を即時化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | - | - |
| 23 | 文書・デザイン | Document Skills (Advanced) | （追加なし: anthropic-skills:pdf/docx/xlsx/pptx） | コードから技術資料やマニュアルを自動で作成し、ドキュメント作成に費やす時間を大幅に削るために使う。 | - | - |
| 24 | 財務・データ | Invoice Organizer Skill | `/invoice-organizer` | 経理・財務の請求書管理・税務準備を自動化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/invoice-organizer) |
| 25 | 財務・データ | Data Journalism Skill | `/data-journalism` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | MIT | [GitHub](https://github.com/jamditis/claude-skills-journalism/tree/HEAD/journalism-core/skills/data-journalism) |
| 26 | 財務・データ | CSV Data Summarizer Skill | `/csv-data-summarizer` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | 記載なし | [GitHub](https://github.com/coffeefuelbump/csv-data-summarizer-claude-skill) |
| 27 | 財務・データ | SaaS Metrics & Revenue Ops Skill | `/saas-metrics-coach` | SaaS事業の財務・成長指標モニタリングをAI化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/finance/skills/saas-metrics-coach) |
| 28 | 財務・データ | DCF Financial Modeling Skill | `/financial-analyst` | 投資判断・M&A・予算策定業務を高精度・短時間で実行の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/finance/skills/financial-analyst) |
| 29 | 財務・データ | International Expansion Skill | `/intl-expansion` | グローバル展開時の市場分析・サプライチェーン含むオペレーションリスク評価の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/c-level-advisor/skills/intl-expansion) |
| 30 | 財務・データ | C-Level Strategy Deck Generator Skill | `/board-deck-builder` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/c-level-advisor/skills/board-deck-builder) |
| 31 | PM・業務・法務 | PhD / Research Integrity Skills | `/phd-compare`<br>`/phd-dataset-curation`<br>`/phd-debug`<br>`/phd-experiment-design`<br>`/phd-launch`<br>`/phd-literature-research`<br>`/phd-paper-check`<br>`/phd-paper-write`<br>`/phd-rebuttal`<br>`/phd-reproduce`<br>`/phd-setup` | 市場調査・競合分析・DD時の資料検証を正確化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/fcakyon/phd-skills/tree/HEAD/plugin/skills/compare) |
| 32 | PM・業務・法務 | Internal Comms Skill | `/internal-comms` | HR・Opsチームの社内コミュニケーションを標準化・効率化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/internal-comms) |
| 33 | PM・業務・法務 | Meeting Insights Analyzer Skill | `/meeting-insights-analyzer` | チームダイナミクス改善・マネジメント効率化に活用の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/meeting-insights-analyzer) |
| 34 | PM・業務・法務 | Tailored Resume Generator Skill | `/tailored-resume-generator` | HR・採用業務の応募書類作成を効率化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/tailored-resume-generator) |
| 35 | PM・業務・法務 | File Organizer Skill | `/file-organizer` | コードから技術資料やマニュアルを自動で作成し、ドキュメント作成に費やす時間を大幅に削るために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/file-organizer) |
| 36 | PM・業務・法務 | Source Verification Skill | `/source-verification` | 市場調査・競合分析・提案資料の信頼性担保を強化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/jamditis/claude-skills-journalism/tree/HEAD/journalism-core/skills/source-verification) |
| 37 | PM・業務・法務 | Fact Check Workflow Skill | `/fact-check-workflow` | プレスリリース・ブログ・提案書の正確性検証を自動化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/jamditis/claude-skills-journalism/tree/HEAD/journalism-core/skills/fact-check-workflow) |
| 38 | PM・業務・法務 | Academic Writing / Research Integrity Skill | `/academic-writing` | 白書・調査レポート・提案書の学術品質を自動化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/jamditis/claude-skills-journalism/tree/HEAD/research-toolkit/skills/academic-writing) |
| 39 | PM・業務・法務 | Connect Skill | `/connect` | GitHubのリポジトリ情報を解析して、コードの修正や新機能の実装をAIに相談しながら進めるために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/connect) |
| 40 | PM・業務・法務 | Kaizen Continuous Improvement Skill | `/kaizen` | 継続的改善文化をAIで支え、組織生産性を長期的に向上の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | GPL-3.0 | [GitHub](https://github.com/NeoLabHQ/context-engineering-kit/tree/HEAD/plugins/kaizen/skills/kaizen) |
| 41 | PM・業務・法務 | Contract & Legal Review Skill | `/contract-and-proposal-writer` | 法務・調達のレビュー工数を大幅削減の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/business-growth/skills/contract-and-proposal-writer) |
| 42 | PM・業務・法務 | Product Management PM Skill | `/product-manager-toolkit` | プロダクトチームの計画立案・調整を効率化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/product-team/skills/product-manager-toolkit) |
| 43 | PM・業務・法務 | Jira & Linear Project Automation Skill | `/jira-expert` | プロジェクト管理のルーチンワークをゼロ化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/project-management/skills/jira-expert) |
| 44 | PM・業務・法務 | n8n MCP Workflow Skill | `/n8n-agents`<br>`/n8n-binary-and-data`<br>`/n8n-code-javascript`<br>`/n8n-code-python`<br>`/n8n-code-tool`<br>`/n8n-error-handling`<br>`/n8n-expression-syntax`<br>`/n8n-mcp-tools-expert`<br>`/n8n-multi-instance`<br>`/n8n-node-configuration`<br>`/n8n-self-hosting`<br>`/n8n-subworkflows`<br>`/n8n-validation-expert`<br>`/n8n-workflow-patterns`<br>`/using-n8n-mcp-skills` | 社内業務プロセス（請求・承認・通知等）をノーコードでAI連携を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/czlonkowski/n8n-mcp/tree/HEAD/data/skills/n8n-agents) |
| 45 | PM・業務・法務 | CHRO Advisor Skill | `/chro-advisor` | 組織戦略・人事施策をAI化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/c-level-advisor/skills/chro-advisor) |
| 46 | PM・業務・法務 | Compliance & GDPR Checklist Skill | `/gdpr-dsgvo-expert` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/ra-qm-team/skills/gdpr-dsgvo-expert) |
| 47 | PM・業務・法務 | Graphify Knowledge Graph Skill | `/llm-wiki` | コードから技術資料やマニュアルを自動で作成し、ドキュメント作成に費やす時間を大幅に削るために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/llm-wiki/skills/llm-wiki) |
| 48 | PM・業務・法務 | PhD-Level Research Integrity Skill (Extended) | （追加なし: No.31 と同じ phd-skills（phd-* として追加済み）） | 市場調査・競合分析の信頼性を保証を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | - | - |
| 49 | セキュリティ | Cloud Security Hardening AWS Skill | `/implementing-aws-security-hub` | コードの脆弱性を自動で見つけ出し、安全なサービスを公開するためのセキュリティチェックに使う。 | Apache-2.0 | [GitHub](https://github.com/mukul975/Anthropic-Cybersecurity-Skills/tree/HEAD/skills/implementing-aws-security-hub) |
| 50 | セキュリティ | Vulnerability Management Patch Prioritization Skill | `/prioritizing-vulnerabilities-with-cvss-scoring` | 脆弱性管理をリスクベースで最適化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0 | [GitHub](https://github.com/mukul975/Anthropic-Cybersecurity-Skills/tree/HEAD/skills/prioritizing-vulnerabilities-with-cvss-scoring) |
| 51 | セキュリティ | Incident Response Ransomware Skill | `/performing-ransomware-response` | インシデント時の事業中断最小化と規制対応（GDPR等）を迅速化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0 | [GitHub](https://github.com/mukul975/Anthropic-Cybersecurity-Skills/tree/HEAD/skills/performing-ransomware-response) |
| 52 | セキュリティ | Threat Hunting Hypothesis Driven Skill | `/building-threat-hunt-hypothesis-framework` | 先進脅威の早期発見を強化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | Apache-2.0 | [GitHub](https://github.com/mukul975/Anthropic-Cybersecurity-Skills/tree/HEAD/skills/building-threat-hunt-hypothesis-framework) |
| 53 | セキュリティ | Zero Trust Architecture Implementation Skill | `/implementing-cisa-zero-trust-maturity-model` | 内部脅威・横移動リスクを低減の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0 | [GitHub](https://github.com/mukul975/Anthropic-Cybersecurity-Skills/tree/HEAD/skills/implementing-cisa-zero-trust-maturity-model) |
| 54 | セキュリティ | Runbook & Incident Response Skill | `/runbook-generator` | 運用のインシデント対応時間を短縮の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/runbook-generator) |
| 55 | セキュリティ | Security Review Action Skill | `/skill-security-auditor` | GitHubのリポジトリ情報を解析して、コードの修正や新機能の実装をAIに相談しながら進めるために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/skill-security-auditor) |
| 56 | 開発 | AI Website Cloner Skill | `/clone-website` | Webアプリの画面デザイン案を出し、ユーザーが使いやすいインターフェースを素早く実装するために使う。 | MIT | [GitHub](https://github.com/JCodesMore/ai-website-cloner-template/tree/HEAD/.agents/skills/clone-website) |
| 57 | 開発 | Caveman Skill | `/caveman` | 長時間Claude Codeセッションのトークン・レスポンスを大幅削減の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0 | [GitHub](https://github.com/JuliusBrussee/caveman/tree/HEAD/skills/caveman) |
| 58 | 開発 | Changelog Generator Skill | `/changelog-generator` | 製品アップデート通知を高速化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/changelog-generator) |
| 59 | 開発 | Developer Growth Analysis Skill | `/developer-growth-analysis` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/developer-growth-analysis) |
| 60 | 開発 | Superpowers Core Skills (TDD/Debugging) | （追加なし: No.61〜69 で中身を個別に追加済み） | 開発ワークフローの計画からレビューまで構造化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | - | - |
| 61 | 開発 | Test-Driven Development Skill | `/test-driven-development` | プログラムのテストコードを自動生成し、動作確認の漏れをなくしてシステムの品質を保つために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/test-driven-development) |
| 62 | 開発 | Systematic Debugging Skill | `/systematic-debugging` | インシデント対応時間を短縮の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/systematic-debugging) |
| 63 | 開発 | Brainstorming Skill | `/brainstorming` | コードから技術資料やマニュアルを自動で作成し、ドキュメント作成に費やす時間を大幅に削るために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/brainstorming) |
| 64 | 開発 | Writing Plans Skill | `/writing-plans` | 大規模開発の計画立案をAI支援で即時化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/writing-plans) |
| 65 | 開発 | Executing Plans Skill | `/executing-plans` | 反復作業の自動化と人間判断のバランスを取って開発生産性をスケールを自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/executing-plans) |
| 66 | 開発 | Dispatching Parallel Agents Skill | `/dispatching-parallel-agents` | 複雑プロジェクトの並列処理を実現し、全体所要時間を劇的に短縮の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/dispatching-parallel-agents) |
| 67 | 開発 | Requesting Code Review Skill | `/requesting-code-review` | コード品質ゲートを自動化し、リリース前バグ混入を防止を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/requesting-code-review) |
| 68 | 開発 | Using Git Worktrees Skill | `/using-git-worktrees` | プログラムのテストコードを自動生成し、動作確認の漏れをなくしてシステムの品質を保つために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/using-git-worktrees) |
| 69 | 開発 | Subagent Driven Development Skill | `/subagent-driven-development` | 長時間自律開発を実現し、人間監督を最小化しつつ品質を維持の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/obra/superpowers/tree/HEAD/skills/subagent-driven-development) |
| 70 | 開発 | MCP Builder Skill | （追加なし: anthropic-skills:mcp-builder） | 外部サービスのAPI連携コードを自動生成し、異なるツールを繋いで業務プロセスを自動化するために使う。 | - | - |
| 71 | 開発 | Skill Creator Skill | （追加なし: anthropic-skills:skill-creator） | プログラムのテストコードを自動生成し、動作確認の漏れをなくしてシステムの品質を保つために使う。 | - | - |
| 72 | 開発 | Webapp Testing Skill | `/webapp-testing` | プログラム of the テストコードを自動生成し、動作確認の漏れをなくしてシステムの品質を保つために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/webapp-testing) |
| 73 | 開発 | Artifacts Builder Skill | （追加なし: anthropic-skills:web-artifacts-builder） | Webアプリの画面デザイン案を出し、ユーザーが使いやすいインターフェースを素べく実装するために使う。 | - | - |
| 74 | 開発 | Langsmith Fetch Skill | `/langsmith-fetch` | AIエージェント開発時の可観測性を向上の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/langsmith-fetch) |
| 75 | 開発 | Observability Designer Skill | `/observability-designer` | 運用トラブル時の調査時間を短縮し、根本解決を促進の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/observability-designer) |
| 76 | 開発 | Senior Architect Skill | `/senior-architect` | システム設計フェーズを高速化し、将来的な拡張性・メンテナンス性を確保の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering-team/skills/senior-architect) |
| 77 | 開発 | Andrej Karpathy Skills | `/karpathy-guidelines` | LLMプロジェクトの過剰実装やミスを防止の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT（SKILL.md記載） | [GitHub](https://github.com/forrestchang/andrej-karpathy-skills/tree/HEAD/skills/karpathy-guidelines) |
| 78 | 開発 | Claude Mem (Persistent Memory) | `/mem-search` | 長期プロジェクトの文脈喪失をゼロ化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0 | [GitHub](https://github.com/thedotmack/claude-mem/tree/HEAD/plugin/skills/mem-search) |
| 79 | 開発 | Claude Code Best Practice Skills | `/weather-fetcher` | 開発ワークフローをagentic engineering化し、レビュー・並行開発・コンテキスト管理を自動化を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/shanraisshan/claude-code-best-practice/tree/HEAD/.claude/skills/weather-fetcher) |
| 80 | 開発 | Professional Claude Skills Marketplace | （追加なし: anthropic-skills:deep-research） | コードから技術資料やマニュアルを自動で作成し、ドキュメント作成に費やす時間を大幅に削るために使う。 | - | - |
| 81 | 開発 | Comprehensive Claude Skills Library (235+) | （追加なし: No.9〜13・27〜30・41〜47・54〜55・75〜97 で個別に追加済み（全235件は入れない）） | ほぼ全ての実務シーンをカバーの作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | - | - |
| 82 | 開発 | CI/CD Pipeline Builder Skill | `/ci-cd-pipeline-builder` | GitHubのリポジトリ情報を解析して、コードの修正や新機能の実装をAIに相談しながら進めるために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/ci-cd-pipeline-builder) |
| 83 | 開発 | Tech Debt Tracker Skill | `/tech-debt-tracker` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/tech-debt-tracker) |
| 84 | 開発 | RAG Architecture Designer Skill | `/rag-architect` | 自社ナレッジ・社内検索の精度を飛躍的に向上の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/rag-architect) |
| 85 | 開発 | Database Designer & Migration Skill | `/database-designer` | 複雑なデータを集計・分析して、ビジネスの意思決定に役立つレポートやグラフを自動で作るために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/database-designer) |
| 86 | 開発 | Codebase Onboarding Skill | `/codebase-onboarding` | 新人エンジニアのオンボーディング期間を大幅短縮を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/codebase-onboarding) |
| 87 | 開発 | Self-Improving Agent Skill | `/self-improving-agent` | AIエージェントを継続的に進化させ、業務適応力を高めるの作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering-team/self-improving-agent/skills/self-improving-agent) |
| 88 | 開発 | Skill Creator & Validator Skill | （追加なし: anthropic-skills:skill-creator） | プログラムのテストコードを自動生成し、動作確認の漏れをなくしてシステムの品質を保つために使う。 | - | - |
| 89 | 開発 | Everything Claude Code Master Skill | （追加なし: 1,089スキルの巨大パックのため見送り（呼び出し精度が落ちる）） | Claude Codeの全機能を即座に最大活用を自動化して、自分の作業時間を減らしつつ成果の質を上げるために使う。 | - | - |
| 90 | 開発 | Generic Self-Evolving Agent Skill | `/agent-designer` | AIエージェントの長期運用で手動チューニングを不要にの作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/agent-designer) |
| 91 | 開発 | om-claude-code-skills-agents Pack | `/azure-policy-assignment`<br>`/azure-policy-defintion`<br>`/azure-resource-graph`<br>`/bicep-best-practices`<br>`/nxtools-dsc-linux`<br>`/powershell-module` | 個人・小規模チームが即戦力AI環境を構築の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/omiossec/om-claude-code-skills-agents/tree/HEAD/skills/azure-policy-assignment) |
| 92 | 開発 | Repomix Codebase Context | `/repomix-explorer` | レガシー移行や大規模リファクタ時の文脈理解を劇的改善の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/yamadashy/repomix/tree/HEAD/skills/repomix-explorer) |
| 93 | 開発 | Claude Squad Multi-Agent Orchestrator Skill | `/agent-workflow-designer` | 市場調査＋提案書作成などを並列処理の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/agent-workflow-designer) |
| 94 | 開発 | Skill Share Skill | `/skill-share` | 社内AIナレッジを組織全体で共有の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/skill-share) |
| 95 | 開発 | Claude Code Best Practice Orchestrator Skill | `/presentation-structure`<br>`/presentation-styling`<br>`/vibe-to-agentic-framework` | Claude Codeの使いこなしを体系化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | MIT | [GitHub](https://github.com/shanraisshan/claude-code-best-practice/tree/HEAD/.claude/skills/presentation/presentation-structure) |
| 96 | 開発 | Claude Mem Persistent Memory Skill (Advanced) | `/knowledge-agent` | 数ヶ月単位のプロジェクトで文脈を完全保持の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0 | [GitHub](https://github.com/thedotmack/claude-mem/tree/HEAD/plugin/skills/knowledge-agent) |
| 97 | 開発 | Skill Tester Skill | `/skill-tester` | プログラムのテストコードを自動生成し、動作確認の漏れをなくしてシステムの品質を保つために使う。 | MIT | [GitHub](https://github.com/alirezarezvani/claude-skills/tree/HEAD/engineering/skills/skill-tester) |
| 98 | その他 | Video Downloader Skill | `/video-downloader` | コンテンツチームの動画アーカイブ・再利用を効率化の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/video-downloader) |
| 99 | その他 | Slack GIF Creator Skill | `/slack-gif-creator` | 社内コミュニケーションの視覚効果を向上の作業をAIに任せて、自分のルーチンワークを効率化するために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/slack-gif-creator) |
| 100 | その他 | Raffle Winner Picker Skill | `/raffle-winner-picker` | プログラムのテストコードを自動生成し、動作確認の漏れをなくしてシステムの品質を保つために使う。 | Apache-2.0（リポジトリ） | [GitHub](https://github.com/ComposioHQ/awesome-claude-skills/tree/HEAD/raffle-winner-picker) |
