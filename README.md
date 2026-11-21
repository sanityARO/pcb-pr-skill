# pcb-pr-skill

**布线卡住时回调布局，接通后减少绕线，交付前核对实铜。**

**Revise congested placement, reduce routing detours, and verify exported copper.**

面向从板级原理图到布局、布线和制造文件核验的 AI 辅助流程。当前验证组合为 **Codex + 嘉立创EDA**；方法可迁移到其它 AI/EDA，执行接口与文件兼容性需适配验证。

An AI-assisted workflow from board schematics to placement, routing and fabrication-data checks, currently exercised with **Codex + 嘉立创EDA (EasyEDA)**. The methods can transfer to other agents and EDA tools with validated adapters and file support.

## 解决什么 · What it helps solve

| 遇到的问题 / Problem | 工作方法 / Method |
|---|---|
| 布局拥挤，到后期才发现无路 / Congestion discovered late | 布局阶段可选试布瓶颈组，反馈器件间距和通道。Trial bottleneck groups during placement and revise spacing/channels. |
| 串联电阻挡住出线 / Resistor banks block escape routes | 回到副本重排器件，按引脚顺序成组扇出。Regroup parts and fan out signals in pin order on a copy. |
| 接通后仍有绕弯、多次换层 / Connected routes take detours | 局部重布，按相同端点比较长度、过孔和回流。Reroute locally and compare length, vias and returns for the same endpoints. |
| 改善目标线却恶化邻网 / Local gains harm neighbors | 成组恢复连接，复扫快速信号、敏感节点和供电回流。Restore group connections and recheck fast signals, sensitive nodes and power returns. |
| 完成提示无法证明制造文件接通 / Completion does not establish CAM connectivity | 对照 Gerber、镀孔和独立焊盘网表检查漏接与短接。Check exported copper and plated drills against an independent pad manifest. |

## 六层芯片测试板案例 · Six-layer test-board example

既有 pcb-skill 与路由器流程在该板遇到拥塞，pcb-pr-skill 整理了从布局回退到继续布线的方法。

Congestion in the existing pcb-skill/router workflow motivated the placement rollback and routing continuation methods collected here.

**中文图示**

<p>
<a href="assets/grouped-fanout.png"><img src="assets/grouped-fanout.png" width="380" alt="固定 FPGA 母座后重排 0 Ω 电阻与 DUT 扇出"></a>
<a href="assets/spi-miso-reroute.png"><img src="assets/spi-miso-reroute.png" width="380" alt="SPI_MISO 在相同三个端点下的局部重布比较"></a>
</p>

**English figures**

<p>
<a href="assets/grouped-fanout-en.png"><img src="assets/grouped-fanout-en.png" width="380" alt="Regrouping 0-ohm resistors and DUT fanout around fixed FPGA headers"></a>
<a href="assets/spi-miso-reroute-en.png"><img src="assets/spi-miso-reroute-en.png" width="380" alt="SPI_MISO before and after local rerouting with the same three endpoints"></a>
</p>

| 已记录结果 / Recorded result | 比较范围 / Scope |
|---|---|
| 全板断点 **52 → 4 → 0** / Board routing gaps | 成组重排后继续局部补线，多个步骤共同完成。Multiple placement and routing steps contributed. |
| SPI_MISO **104.50 → 102.72 mm**，信号过孔 **11 → 9** / Signal vias | 两版均接通 U2.25、R269.2、J123.4，长度包含调试支路。Same three endpoints, including the debug branch. |
| **303 nets / 1,134 pads** | 0.025 mm 栅格 CAM 连通核验通过；记录的原生 DRC 为 0 项。CAM connectivity passed at 0.025 mm resolution; native DRC reported zero items. |

图片展示实际布局与同坐标走线比较。已完成该版布线，**待打板验证**；几何改善尚未证明信号质量或功能改善。

The figures show actual placement and route comparisons in common coordinates. Routing is complete for the recorded revision; **fabrication and hardware validation are pending**. Geometric improvements have not established signal-integrity or functional gains.

## 工作流程 · Workflow

```mermaid
flowchart TD
    A["布局与通道预算<br/>Placement and channel budget"] --> B["可选瓶颈组试布<br/>Optional bottleneck trial"]
    B -- "拥塞或回流不足 / Revise" --> A
    B -- "评审并批准 / Review and approve" --> C["成组布线<br/>Grouped routing"]
    A -- "评审批准 / Approved" --> C
    C -- "局部拥塞 / Congestion" --> A
    C -- "阶段完成或需实铜 / Stage boundary or copper-dependent decision" --> D["重铺铜与邻域复核<br/>Pours and neighborhood checks"]
    D -- "出现回归 / Regression" --> A
    D --> E["读回与按交付点验收<br/>Readback and scoped acceptance"]
```

布局阶段在已授权副本上试最难扇出、整组入口及必要测试支路，用实际线宽、孔盘和回流空间提前发现拥塞。用户明确要求不布线时采用几何预测。保存布局检查点供后续恢复，图中进入成组布线的路径均需已有布线授权，超出授权范围的固定项调整须先复审。

Use authorized copies to trial difficult escapes, group entrances and test branches with realistic widths, via pads and return space. For layout-only requests, use geometric prediction. Routing requires existing authorization; changes beyond the approved scope return to review.


### 规则何时使用 · When rules apply

| 时机 / Stage | Codex 判断 / Engineering judgment |
|---|---|
| 放件 / Placement | 参考电路适用性、安装孔铜归属、去耦回路和测量边界。Reference suitability, mounting-copper connectivity, decoupling loops and measurement boundaries. |
| 走线 / Routing | 线宽/细颈、差分主通路时序、支路、泪滴、侧地及换层回流。Widths/necks, differential main-path timing, branches, teardrops, guards and return transitions. |
| 验收 / Acceptance | 同版原理图/ECO 与 PCB，最终实铜及受改动影响的工程条件。Matching schematic/ECO and PCB revisions, final copper and affected engineering conditions. |

**默认建议可覆盖，必须检查项按场景触发。** 可选低压测试板预设为普通非阻抗信号 **≥10 mil**、供电干线 **≥20 mil**；按电流、铜厚、压降与温升调整，电压同时约束净距、绝缘和额定值。阻抗线、细脚和敏感节点按专门要求确定。详见[设计规则](references/placement-routing.md#设计时使用规则)。

**Defaults are overridable; required checks are conditional.** An optional low-voltage preset starts at **≥10 mil** for ordinary signals and **≥20 mil** for power trunks. Adjust for current, copper, drop and heating; voltage also constrains clearance, insulation and ratings. Impedance-controlled routes, fine-pitch escapes and sensitive nodes use their specific requirements.

| 场景 / Scenario | 默认建议 / Default | 必须检查的触发条件 / Required when applicable |
|---|---|---|
| 参考与测量 / References and measurement | 借鉴方法，不照搬参数。Reuse methods, not parameters. | 复用前核对功能、频带及源/负载；供电测流核对量程、误差与储能边界。Check function, band and source/load before reuse; supply-current measurements need range, error and stored-energy boundaries. |
| 安装孔 / Mounting holes | 孔型按机械需求。Choose holes for mechanical needs. | 金属紧固件/孔边铜需明确浮空、GND 或机壳地，并检查全层净距。Define floating, GND or chassis connectivity and all-layer clearances for metal fasteners or hole copper. |
| 调长与修形 / Tuning and copper shaping | 先保参考和对称，择点加泪滴。Prioritize references and symmetry; use teardrops selectively. | 按主通路时序预算调长，支路单列；阻抗线修形核对局部阻抗/电容，电源核对最窄截面。Tune to main-path timing budgets, assess branches separately; check local impedance/capacitance or power bottlenecks after shaping. |
| 地与守卫 / Grounds and guards | 分区与连续回流优先。Prioritize partitioning and continuous returns. | 地别名/短接符号不等于隔离；高阻侧地需检查漏电和附加电容。Ground aliases/ties do not establish isolation; guards near high-impedance nodes need leakage and capacitance checks. |

| 已有自动能力 / Existing automation | 范围 / Scope |
|---|---|
| 所选 EDA/CLI 的 DRC / Backend DRC | 工具支持且实际生效的规则。Supported, active rules. |
| `board-job.mjs` | easyeda-api 路径的快照、铺铜保存、DRC 和导出作业。Snapshots, pour/save, DRC and exports through easyeda-api. |
| `cam-check.py` + pcb-skill 解析器 / Parsers | 开路、异网共铜、缺铜焊盘，受文件格式及分辨率限制。Opens, shared copper and missing pad copper within format/resolution limits. |

表中工程规则由 Codex 判断，必要时由人工、仿真或实测确认，并非新增自动检查。脚本不自动验证参考电路适用性、机械接触、阻抗/串扰、载流与回流质量、去耦效果或功耗测量精度；集中成组布线，避免每布一两根就重铺、导出或中断；阶段结束统一重建，依赖实铜的决策按[例外条件](references/placement-routing.md#集中布线与阶段铺铜)提前核验。

The engineering rules above guide Codex judgment, with human review, simulation or measurement as needed; they are not new automated checks. Scripts do not establish reference-circuit suitability, mechanical contact, impedance/crosstalk, current capacity or return quality, decoupling effectiveness or power-measurement accuracy. Route in groups without interrupting every few traces to repour or export. Rebuild at stage boundaries, or earlier when a decision depends on current filled copper.

## 与上游的关系 · Relationship to upstream

| 工具 / Tool | 分工与验证范围 / Role and validation |
|---|---|
| [PcbCliTool](https://github.com/cc38324/PcbCliTool) | 优先本地工程；已验证 **0.3.0 / Windows x64** 的官方 Demo 和特定六层工程读取、项目脚本修改后的读回、重铺铜、DRC 与诊断 CAM 导出。自带路由能力逐命令验证；开窗导出等限制见[版本记录](references/easyeda-cam.md#工具能力与版本记录)。Native readback, repouring, DRC and diagnostic CAM tested on selected six-layer files after project-script edits. Built-in routing requires separate validation; see the version notes for export limits. |
| [easyeda-api](https://github.com/easyeda/easyeda-api-skill) | 实时客户端与 SDK 操作，按操作选用，明确同步与单一写入者。记录组合 **1.1.36 + 嘉立创EDA 4.1.99**。Alternative live backend; recorded configuration shown. |
| [pcb-skill](https://github.com/daishuge/pcb-skill/tree/6e939b64907e3c63236c7522c511af5d7d1afaad) | 提供外部布线与 CAM 工具；本仓库沿用其解析器，补充布局回退、候选比较和验收流程。Supplies routing/CAM tooling; this skill adds placement rollback, candidate comparison and verification procedures. |

## 安装与试用 · Install and try

将仓库安装到 Codex 技能目录，选一个执行入口，按该工具文档配置。PcbCliTool 读取随包 `SKILL.md` 并核对 `--version`；easyeda-api 需连接桌面网关，现场脚本使用 Node.js 18+。

Install into the Codex skill directory and configure one backend using its documentation. Read PcbCliTool's bundled `SKILL.md` and record `--version`; easyeda-api needs a connected desktop bridge and Node.js 18+ for live scripts.

<details>
<summary>从空目录运行 CAM 示例 / Run the CAM fixture from scratch</summary>

在测试项目的 PowerShell 中执行。示例生成临时双层板，分别检查正常、开路和短路，无需连接 EDA。

Run in PowerShell from a test project. The temporary two-layer fixture checks good, open and shorted cases without an EDA connection.

```powershell
New-Item -ItemType Directory -Force .agents/skills | Out-Null
git clone https://github.com/sanityARO/pcb-pr-skill.git .agents/skills/pcb-pr-skill
git clone https://github.com/daishuge/pcb-skill.git pcb-skill
git -C pcb-skill checkout --detach 6e939b64907e3c63236c7522c511af5d7d1afaad
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install numpy scipy
.\.venv\Scripts\python.exe .agents/skills/pcb-pr-skill/scripts/test-cam.py ./pcb-skill
```

macOS/Linux 使用 `mkdir -p .agents/skills`、`python3 -m venv .venv` 和 `.venv/bin/python`。三个预期结果依次为 `True / False / False`，退出码为 0 表示全部检出符合预期。

On macOS/Linux, use the directory/interpreter commands above. Expected results are `True / False / False`; exit code 0 means all cases matched expectations.

已记录 Windows 环境为 Python 3.10.5、NumPy 2.2.6、SciPy 1.15.3。此示例验证检查器；六层板结果来自上面的工程案例。

Recorded Windows environment used Python 3.10.5, NumPy 2.2.6 and SciPy 1.15.3. This fixture tests the checker; the six-layer results come from the board case above.

</details>

<details>
<summary>用于自己的板图 / Use your own board</summary>

在技能目录运行，替换路径和 UUID。首条仅适用于已连接的 easyeda-api。CAM 输入需同版 Gerber、镀孔和独立焊盘网表。

Run from the skill directory with your paths and UUIDs. The first command needs a live easyeda-api connection. CAM inputs need a common revision and origin.

```text
node scripts/board-job.mjs snapshot PROJECT_UUID BOARD_UUID before.epcb
python scripts/cam-check.py check.zip manifest.json report.json --pcb-skill PATH_TO_PCB_SKILL --resolution 0.025
```

当前脚本支持正片铜和圆形贯通镀孔。临界间距用更细网格或矢量 CAM 复核。清单格式和其它限制见[操作参考](references/easyeda-cam.md)。

The checker supports positive copper and circular plated through-holes. Recheck marginal features with finer grids or vector CAM. See the [manifest and limitations](references/easyeda-cam.md).

</details>

[技能入口 / Instructions](SKILL.md) · [布局、规则与回退 / Placement and rollback](references/placement-routing.md) · [现场作业与 CAM / Jobs and CAM](references/easyeda-cam.md)

欢迎在副本上试用，并在 issue 中提供工具版本、问题位置及可分享的最小示例。

Try it on a copy and report the tool versions, problem location and a shareable minimal example in an issue.

## 许可证 · License

本仓库采用 [MIT 许可证](LICENSE)。所引用或依赖的第三方工具仍遵循各自的许可证；本许可证不替代它们的许可条款。

This repository is licensed under the [MIT License](LICENSE). Referenced and dependent third-party tools remain subject to their own licenses.
