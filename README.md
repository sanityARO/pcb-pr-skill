# pcb-pr-skill

用于 Codex 和嘉立创EDA 的 PCB 布局、布线和制造文件核验技能。面向需要把芯片原理图做成可调试测试板的设计者，以及需要比较布线方案、审查回流和交付 Gerber 的 PCB 工程师。

A Codex skill for PCB placement, routing and manufacturing-data verification in EasyEDA. It helps chip designers bring up mixed-signal test boards and PCB engineers compare routing candidates and check the copper submitted for fabrication.

## 工作流程 · Workflow

| 阶段 / Stage | 操作与交付物 / Actions and evidence |
|---|---|
| 冻结基线 / Freeze | 记录工程及板 UUID、网表、固定器件、引脚映射、机械与叠层约束，保存板源。Record the project and board UUIDs, netlist, fixed parts, pin map, mechanical constraints and stackup. Save a source snapshot. |
| 布局 / Place | 先安排接口、光窗、探测空间和供电回流。按 DUT 管脚顺序对齐 FPGA 电阻组，给模拟偏置留独立通道。Reserve mechanical, probing and return-path space. Align resistor banks with DUT pin order and reserve an analog bias corridor. |
| 试布与回退 / Route and revise | 在副本按端点组成组扇出。若串联电阻区形成瓶颈，局部拆线、调整间距、恢复受影响的控制线，再以相同端点比较断点、长度、过孔和回流。On a copy, escape signals in groups. At a bottleneck, rip up locally, revise spacing, restore displaced control nets and compare the same endpoints across candidates. |
| 实铜验收 / Verify | 一个布线阶段结束后统一重建铺铜。保存并重开正式板，核对身份、运行原生 DRC，对同版 Gerber、钻孔与带网焊盘表做连通检查。After each routing stage, rebuild pours, save and reopen the target board. Run native DRC and check its Gerbers and drills against an independently derived pad manifest. |

## 与上游的关系 · Relationship to upstream

| 项目 / Project | 用途与边界 / Scope |
|---|---|
| [easyeda-api](https://github.com/easyeda/easyeda-api-skill) | 提供 SDK 文档、桌面扩展与本机网关，负责现场读写。Provides the SDK reference, desktop extension and local bridge for live board access. |
| [daishuge/pcb-skill](https://github.com/daishuge/pcb-skill/tree/6e939b64907e3c63236c7522c511af5d7d1afaad) | 参考的上游版本覆盖更广的 PCB 制作流程，包括布局、布线和 Gerber 工具。本技能的 CAM 检查调用该仓库的解析代码。The upstream workflow covers a broader board-development cycle, including placement, routing and Gerber tools. Our CAM checker imports its parser from a local checkout. |
| **pcb-pr-skill** | 针对 spadfe 中单靠路由完成提示无法判定的三件事补充操作和脚本：拥塞时怎样回退布局、超时后如何确认操作落在哪张板、导出铜层是否连接了所有预期焊盘。Adds procedures for three decisions encountered on spadfe: when to revise placement, how to identify the board and job after a timeout, and how to check exported copper against every expected pad. |

布局和布线采用 Codex、EDA 工具及可选外部路由器协同完成。仓库内脚本负责现场作业和制造文件核验。Placement and routing use Codex, EDA tools and an optional external router. The bundled scripts handle board jobs and CAM checks.

## 安装与复现 · Installation and reproduction

1. 将本仓库放入 Codex 技能目录下的 `pcb-pr-skill/`，确保 `SKILL.md` 位于该目录根部。Install this repository as `~/.codex/skills/pcb-pr-skill/`, with `SKILL.md` at its root.
2. 操作实际板图需安装 easyeda-api，按其说明加载 `run-api-gateway` 并连接桌面客户端，使用 Node.js 18+。已验证组合为 easyeda-api 1.1.36 与嘉立创EDA 4.1.99。For live jobs, connect the desktop extension to its bridge and use Node.js 18+. The recorded configuration used easyeda-api 1.1.36 with EasyEDA 4.1.99.
3. 离线 CAM 复现需 Python、NumPy、SciPy 及上表所链接提交的 pcb-skill 本地副本。外部自动布线可选 FreeRouting；运行下列检查无需启动路由器。Offline CAM checks require Python, NumPy, SciPy and a local checkout of the linked pcb-skill revision. FreeRouting is optional for external routing trials.

从本仓库根目录运行。第一条命令生成并验证一个双层样板的正常、开路、短路三种情况，无需打开 EDA。Run from the repository root. The first command generates and checks connected, open and shorted fixtures without a live EDA session.

```text
python scripts/test-cam.py PATH_TO_PCB_SKILL
node scripts/board-job.mjs snapshot PROJECT_UUID BOARD_UUID before.epcb
python scripts/cam-check.py check.zip manifest.json report.json --pcb-skill PATH_TO_PCB_SKILL --resolution 0.025
```

真实板需提供同一修订、同一坐标原点的铜层、金属化钻孔和网表焊盘清单。脚本支持正片铜层及圆形贯通镀孔。栅格步长应小于需要辨别的铜颈和间隙，临界位置需更细网格或矢量 CAM 复核。For a real board, supply copper, plated drills and a pad manifest with a common revision and origin. The checker supports positive copper and circular plated through-holes. Resolve narrow features with a finer grid or vector CAM.

## spadfe 测试板 · Worked example

六层 ToF/DVS 测试板包含倒装 QFP144、光学开窗、FPGA 接口、160 MHz 时钟、灯板 LVDS 和阵列供电。冻结版记录 52 处断点。保留固定接口并重排 FPGA 电阻组与 DUT 两侧扇出后，试布收敛到 4 处，随后补齐。正式板原生 DRC 报告 0 项；按 0.025 mm 网格核对导出铜，303 个预期网络的 1,134 个焊盘通过连通检查。灯板 LVDS 主路径和调试支路需分别检查参考面，主路径的覆盖结果不能外推到支路。

The six-layer spadfe ToF/DVS test board combines an inverted QFP144, an optical aperture, FPGA headers, a 160 MHz clock, LVDS lighting control and an array supply. The frozen design had 52 routing gaps. Regrouping the FPGA resistors and DUT escapes around fixed interfaces reduced the trial to four gaps, which were then closed. Native DRC reported zero items on the formal board. Exported copper passed the connectivity check for 303 expected nets and 1,134 pads on a 0.025 mm grid. The LVDS main path and debug stub were evaluated separately. These results document CAD and CAM checks. Impedance, transient droop and imaging performance require separate measurement.

公开示例提供方法与结果摘要；上述命令可在合成样板或读者自己的板上运行。The public example documents the method and recorded results. Reproduce the checker on its synthetic fixture or apply it to your own board.

## 操作参考 · Operator references

- [技能入口 / Codex instructions](SKILL.md)
- [布局、布线与回退 / Placement, routing and rollback](references/placement-routing.md)
- [板图作业、输入格式及 CAM 限制 / Board jobs, manifest and CAM limitations](references/easyeda-cam.md)
